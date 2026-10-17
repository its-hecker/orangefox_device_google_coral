// Host regression coverage for the actual patched OrangeFox storage methods.
// Real directory IO is confined to a temporary tree; mounts, fscrypt, SELinux
// and MTP are substituted. This does not establish Android/device behavior.
#include <sys/mount.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/vfs.h>
#include <linux/fs.h>
#include <dirent.h>
#include <fcntl.h>
#include <unistd.h>
#include <cassert>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <map>
#include <string>

using std::string;
namespace fs = std::filesystem;
static fs::path sandbox;
static long filesystem_type;
static bool filesystem_ro, mount_ok, metadata_ok, binding_ok, busy_bind;
static bool encrypted_media, flags_ok, scan_ok, label_ok, mtp_enabled;
static int bound, unbound, mtp_adds, fbe_attempts, fde_attempts, adopted_attempts;
static int metadata_attempts, formatted, details_updates;
static std::map<string, string> values;

#define TW_IS_FBE "tw_is_fbe"
#define TW_IS_ENCRYPTED "tw_is_encrypted"
#define TW_IS_DECRYPTED "tw_is_decrypted"
#define TW_CRYPTO_PWTYPE "tw_crypto_pwtype"
#define TW_INTERNAL_PATH "tw_internal_path"
#define TW_INCLUDE_CRYPTO
#define TW_INCLUDE_FBE_METADATA_DECRYPT
#define USE_FSCRYPT
#define TW_EXCLUDE_APEX
#define TW_FORMAT_DATA_SCRIPT "none"
#define CRYPT_TYPE_DEFAULT 1
#define LOGINFO(...) do {} while (0)
#define LOGERR(...) do {} while (0)

static string mapped(const char* path) {
    return (sandbox / string(path).substr(1)).string();
}
static int host_statfs(const char* path, struct statfs* info) {
    *info = {};
    info->f_type = filesystem_type;
    info->f_flags = filesystem_ro ? MS_RDONLY : 0;
    return 0;
}
static DIR* host_opendir(const char* path) {
    if (!scan_ok) { errno = EACCES; return nullptr; }
    return ::opendir(mapped(path).c_str());
}
static int host_lstat(const char* path, struct stat* info) {
    return ::lstat(mapped(path).c_str(), info);
}
static int host_mkdir(const char* path, mode_t mode) {
    return ::mkdir(mapped(path).c_str(), mode);
}
static int host_open(const char* path, int flags) {
    return ::open(mapped(path).c_str(), flags);
}
static int host_ioctl(int fd, unsigned long request, int* attributes) {
    assert(request == FS_IOC_GETFLAGS);
    if (!flags_ok) { errno = EOPNOTSUPP; return -1; }
    *attributes = encrypted_media ? FS_ENCRYPT_FL : 0;
    return 0;
}
static int host_chown(const char* path, uid_t uid, gid_t gid) {
    // CI need not run as root. Record ownership separately, check requested IDs.
    assert(uid == 1023 && gid == 1023);
    values["media_owner"] = "1023:1023";
    return 0;
}
static int host_chmod(const char* path, mode_t mode) {
    return ::chmod(mapped(path).c_str(), mode);
}
static int host_umount(const char* path, int flags) {
    assert(string(path) == "/sdcard");
    if (busy_bind) { errno = EBUSY; return -1; }
    ++unbound;
    errno = EINVAL;
    return -1;
}
static void* selinux_handle = reinterpret_cast<void*>(1);
static int selabel_lookup(void*, char** context, const char* path, int mode) {
    assert(string(path) == "/data/media" && mode == S_IFDIR);
    *context = strdup("u:object_r:media_rw_data_file:s0");
    return 0;
}
static int lsetfilecon(const char* path, const char* context) {
    return label_ok ? 0 : -1;
}
static void freecon(char* context) { free(context); }

struct DataManager {
    static void SetValue(const string& name, int value) { values[name] = std::to_string(value); }
    static void SetValue(const string& name, const string& value) { values[name] = value; }
    static int GetIntValue(const string& name) { return std::stoi(values.at(name)); }
};
struct TWPartition {
    string Mount_Point = "/data", Key_Directory = "/metadata/vold/metadata_encryption";
    string Actual_Block_Device = "/dev/block/sda15", Decrypted_Block_Device = "/dev/block/dm-4";
    string Current_File_System = "f2fs", Storage_Path = "/data/media/0";
    string Symlink_Mount_Point = "/sdcard";
    bool Has_Data_Media = true, Mount_Read_Only = false, mounted = true;
    bool Is_FBE = true, Is_Encrypted = true, Is_Decrypted = false;
    unsigned int MTP_Storage_ID = 65537;
    bool Prepare_Fresh_Data_Media();
    bool Mount(bool) { return mount_ok && mounted; }
    bool Is_Mounted() { return mounted; }
    bool UnMount(bool) { mounted = false; return true; }
    void Setup_Data_Media() {
        assert(!fs::exists(sandbox / "data/media/0"));
        Storage_Path = "/data/media";
        fs::create_directories(sandbox / "sdcard");
    }
    bool Bind_Mount(bool) {
        if (!binding_ok) return false;
        assert(fs::is_directory(sandbox / "data/media"));
        ++bound;
        return true;
    }
    bool Decrypt_FBE_DE() {
        ++fbe_attempts;
        Is_FBE = true;
        Is_Decrypted = false;
        return true;
    }
    bool Wipe_Encryption() {
        ++formatted;
        fs::remove_all(sandbox / "data");
        fs::create_directories(sandbox / "data");
        mounted = true;
        return true;
    }
};
static TWPartition data_partition, metadata_partition;
struct TWPartitionManager {
    void Decrypt_Data();
    int Format_Data();
    TWPartition* Find_Partition_By_Path(const string& path) {
        return path == "/data" ? &data_partition : &metadata_partition;
    }
    bool Mount_By_Path(const string&, bool) { metadata_partition.mounted = true; return true; }
    void Set_Crypto_State() {}
    void Set_Crypto_Type(const string&) {}
    int Decrypt_Device(const string&) { assert(false); return -1; }
    void Decrypt_Adopted() { ++adopted_attempts; }
    bool Check_Pending_Merges() { return true; }
    bool Wipe_By_Path(const string&) { return true; }
    void Update_System_Details() { ++details_updates; }
    void Add_MTP_Storage(unsigned int id) {
        assert(id == data_partition.MTP_Storage_ID);
        if (mtp_enabled) ++mtp_adds;
    }
} PartitionManager;
static string additional_fstab = "/tmp/additional.fstab";
namespace android {
namespace base {
static string GetProperty(const string&, const string&) { return "/dev/block/dm-4"; }
static bool GetBoolProperty(const string&, bool) { return false; }
}
namespace vold {
static bool fscrypt_mount_metadata_encrypted(const string&, const string&, bool, bool,
                                            const string&, const string&) {
    ++metadata_attempts;
    if (metadata_ok) data_partition.mounted = true;
    return metadata_ok;
}
}
}
struct TWFunc {
    static bool Block_Operations_Until_Reboot() { return false; }
    static bool Path_Exists(const string&) { return false; }
    static void check_and_run_script(const string&, const string&) {}
};
static int cryptfs_get_password_type() { ++fde_attempts; return 4; }
namespace msg { constexpr int kError = 1; }
struct Msg {
    Msg(int, const char*) {}
    Msg& operator()(const char*) { return *this; }
};
template <typename T> static void gui_msg(T) {}
static void gui_err(const char*) {}

#define statfs(...) host_statfs(__VA_ARGS__)
#define opendir host_opendir
#define lstat host_lstat
#define mkdir host_mkdir
#define open host_open
#define ioctl host_ioctl
#define chown host_chown
#define chmod host_chmod
#define umount2 host_umount
#include "fresh_data_methods.inc"
#undef statfs
#undef opendir
#undef lstat
#undef mkdir
#undef open
#undef ioctl
#undef chown
#undef chmod
#undef umount2

static int cases = 0;
static void reset() {
    fs::remove_all(sandbox);
    fs::create_directories(sandbox / "data");
    data_partition = TWPartition{};
    metadata_partition = TWPartition{};
    filesystem_type = 0xF2F52010;
    filesystem_ro = busy_bind = encrypted_media = mtp_enabled = false;
    mount_ok = metadata_ok = binding_ok = flags_ok = scan_ok = label_ok = true;
    bound = unbound = mtp_adds = fbe_attempts = fde_attempts = adopted_attempts = 0;
    metadata_attempts = formatted = details_updates = 0;
    values = {{TW_IS_FBE, "1"}, {TW_IS_ENCRYPTED, "1"}, {TW_IS_DECRYPTED, "0"},
              {TW_CRYPTO_PWTYPE, "4"}, {TW_INTERNAL_PATH, "/data/media/0"},
              {"tw_mtp_enabled", "0"}};
    ++cases;
}
static void expect_locked() {
    assert(data_partition.Is_Encrypted && !data_partition.Is_Decrypted && data_partition.Is_FBE);
    assert(values.at(TW_IS_ENCRYPTED) == "1" && values.at(TW_IS_DECRYPTED) == "0");
    assert(!mtp_adds && !bound);
}
static void expect_ready() {
    assert(!data_partition.Is_Encrypted && data_partition.Is_Decrypted && !data_partition.Is_FBE);
    assert(values.at(TW_IS_ENCRYPTED) == "0" && values.at(TW_IS_DECRYPTED) == "1");
    assert(values.at(TW_INTERNAL_PATH) == "/data/media");
    assert(values.at("tw_storage_path") == "/data/media");
    assert(values.at("tw_settings_path") == "/data/media");
    assert(data_partition.Decrypted_Block_Device == "/dev/block/dm-4");
    assert(!fs::exists(sandbox / "data/media/0"));
    assert(bound && !fbe_attempts && !fde_attempts);
    assert(values.at("tw_mtp_enabled") == "0"); // Do not override the user's MTP setting.
}
int main(int argc, char** argv) {
    assert(argc == 2);
    sandbox = fs::path(argv[1]) / "filesystem";

    reset();
    assert(data_partition.Prepare_Fresh_Data_Media());
    expect_ready();
    assert(!mtp_adds && values.at("media_owner") == "1023:1023");
    struct stat media_info;
    assert(::stat((sandbox / "data/media").c_str(), &media_info) == 0);
    assert((media_info.st_mode & 0777) == 0770);

    reset();
    filesystem_type = 0xEF53;
    fs::create_directory(sandbox / "data/lost+found");
    fs::create_directory(sandbox / "data/recovery");
    mtp_enabled = true;
    PartitionManager.Decrypt_Data();
    expect_ready();
    assert(mtp_adds == 1);

    reset();
    data_partition.mounted = false;
    PartitionManager.Decrypt_Data();
    expect_ready();
    assert(metadata_attempts == 1);

    reset();
    fs::create_directories(sandbox / "data/media/Fox");
    std::ofstream(sandbox / "data/media/rom.zip") << "keep staged files";
    PartitionManager.Decrypt_Data();
    expect_ready();
    string saved;
    std::getline(std::ifstream(sandbox / "data/media/rom.zip"), saved);
    assert(saved == "keep staged files");

    for (const string name : {"unencrypted/key", "misc/vold/user_keys", "system_de/0",
                              "user_de/0", "user/0", "system", "app", "unknown"}) {
        reset();
        fs::create_directories(sandbox / "data" / name);
        assert(!data_partition.Prepare_Fresh_Data_Media());
        expect_locked();
        assert(!fs::exists(sandbox / "data/media"));
    }

    reset();
    data_partition.mounted = false;
    fs::create_directories(sandbox / "data/unencrypted/key");
    PartitionManager.Decrypt_Data();
    assert(metadata_attempts == 1 && fbe_attempts == 1 && !bound);
    expect_locked();

    reset();
    fs::create_directories(sandbox / "data/media/0");
    assert(!data_partition.Prepare_Fresh_Data_Media());
    expect_locked();

    reset();
    fs::create_directory(sandbox / "data/media");
    fs::create_symlink("/missing", sandbox / "data/media/0");
    assert(!data_partition.Prepare_Fresh_Data_Media());
    expect_locked();

    for (const string name : {"media", "recovery", "lost+found"}) {
        reset();
        fs::create_symlink("/tmp", sandbox / "data" / name);
        assert(!data_partition.Prepare_Fresh_Data_Media());
        expect_locked();
    }

    for (int failure = 0; failure < 12; ++failure) {
        reset();
        switch (failure) {
            case 0: mount_ok = false; break;
            case 1: data_partition.Mount_Read_Only = true; break;
            case 2: filesystem_ro = true; break;
            case 3: filesystem_type = 0x01021994; break; // tmpfs
            case 4: scan_ok = false; break;
            case 5: flags_ok = false; break;
            case 6: encrypted_media = true; break;
            case 7: binding_ok = false; break;
            case 8: busy_bind = true; break;
            case 9: label_ok = false; break;
            case 10: data_partition.Key_Directory.clear(); break;
            case 11: data_partition.Has_Data_Media = false; break;
        }
        assert(!data_partition.Prepare_Fresh_Data_Media());
        expect_locked();
    }

    reset();
    data_partition.mounted = false;
    metadata_ok = false;
    PartitionManager.Decrypt_Data();
    expect_locked();
    assert(!fs::exists(sandbox / "data/media"));

    reset();
    fs::create_directories(sandbox / "data/unencrypted/key");
    assert(PartitionManager.Format_Data());
    expect_ready();
    assert(formatted == 1 && details_updates == 1);
    std::printf("Fresh-data storage regression checks passed: %d cases\n", cases);
}
