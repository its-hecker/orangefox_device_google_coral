#!/usr/bin/env python3
"""Recognize an AArch64 constant assignment to OrangeFox's maintainer key.

Clang can construct a short libc++ string with MOV/STR instructions instead
of a contiguous string in .rodata. Read that assignment without executing
Android code. Unknown values remain unknown; only a fully recovered key and
value passed together to a call can satisfy this check.
"""
import io
import struct


def has_inline_maintainer(binary, expected):
    from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
    from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_REG, ARM64_OP_MEM
    from elftools.elf.elffile import ELFFile
    from elftools.dwarf.callframe import FDE

    elf = ELFFile(io.BytesIO(binary))
    if elf['e_machine'] != 'EM_AARCH64' or not elf.little_endian:
        return False
    text = elf.get_section_by_name('.text')
    if text is None or len(expected.encode()) < 2:
        return False
    data, address = text.data(), text['sh_addr']
    prefix = int.from_bytes(expected.encode()[:2], 'little')
    candidates = []
    for off in range(0, len(data) - 3, 4):
        word = struct.unpack_from('<I', data, off)[0]
        if word & 0x7f800000 == 0x52800000 and (word >> 5) & 65535 == prefix:
            candidates.append(address + off)
    if not candidates:
        return False
    frames = [f for f in elf.get_dwarf_info().EH_CFI_entries() if isinstance(f, FDE)]
    loads = [s for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD']
    decoder = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    decoder.detail = True

    for candidate in candidates:
        frame = next((f for f in frames if f['initial_location'] <= candidate <
                      f['initial_location'] + f['address_range']), None)
        if frame is None or candidate - frame['initial_location'] > 65536:
            continue
        start = frame['initial_location']
        end = min(start + frame['address_range'], candidate + 512)
        registers, memory = {'sp': 1 << 48}, {}

        def key(name):
            return {'fp': 'x29', 'lr': 'x30'}.get(name, 'x' + name[1:] if name.startswith('w') else name)

        def reg(number):
            name = decoder.reg_name(number)
            if name in ('xzr', 'wzr'):
                return 0
            value = registers.get(key(name))
            return value & 0xffffffff if value is not None and name.startswith('w') else value

        def put(number, value):
            name = decoder.reg_name(number)
            if name not in ('xzr', 'wzr'):
                registers[key(name)] = value & 0xffffffff if value is not None and name.startswith('w') else value

        def read(location, size):
            if location is None:
                return None
            result = []
            for a in range(location, location + size):
                if a in memory:
                    value = memory[a]
                else:
                    segment = next((s for s in loads if s['p_vaddr'] <= a <
                                    s['p_vaddr'] + s['p_filesz']), None)
                    value = binary[segment['p_offset'] + a - segment['p_vaddr']] if segment else None
                if value is None:
                    return None
                result.append(value)
            return bytes(result)

        def write(location, size, value):
            if location is not None:
                for n in range(size):
                    memory[location + n] = None if value is None else (value >> (n * 8)) & 255

        def string(location):
            header = read(location, 1)
            if not header or header[0] & 1 or header[0] >> 1 > 22:
                return None
            value = read(location + 1, header[0] >> 1)
            terminator = read(location + 1 + (header[0] >> 1), 1)
            return value if terminator == b'\0' else None

        def scalar(operand):
            value = operand.imm if operand.type == ARM64_OP_IMM else reg(operand.reg) if operand.type == ARM64_OP_REG else None
            return value << operand.shift.value if value is not None else None

        for instruction in decoder.disasm(data[start - address:end - address], start):
            op, operands = instruction.mnemonic, instruction.operands
            if op == 'bl':
                if string(registers.get('x1')) == b'of_maintainer' and string(registers.get('x2')) == expected.encode():
                    return True
                for n in range(19):
                    registers.pop('x' + str(n), None)
                continue
            if op in ('mov', 'movz', 'adr', 'adrp') and len(operands) == 2:
                put(operands[0].reg, scalar(operands[1]))
                continue
            if op == 'movk':
                previous = reg(operands[0].reg)
                shift = operands[1].shift.value
                value = None if previous is None else (previous & ~(65535 << shift)) | (operands[1].imm << shift)
                put(operands[0].reg, value)
                continue
            if op in ('add', 'sub') and len(operands) == 3:
                a, b = scalar(operands[1]), scalar(operands[2])
                put(operands[0].reg, None if a is None or b is None else a + b if op == 'add' else a - b)
                continue
            mem = next((o.mem for o in operands if o.type == ARM64_OP_MEM), None)
            if mem is not None and op.startswith(('ldr', 'ldur', 'str', 'stur', 'stp')):
                base = reg(mem.base)
                index = reg(mem.index) if mem.index else 0
                location = None if base is None or index is None else base + index + mem.disp
                if op == 'stp':
                    size = 4 if decoder.reg_name(operands[0].reg).startswith('w') else 8
                    write(location, size, reg(operands[0].reg))
                    write(None if location is None else location + size, size, reg(operands[1].reg))
                else:
                    size = 1 if op.endswith('b') else 2 if op.endswith('h') else 4 if decoder.reg_name(operands[0].reg).startswith('w') else 8
                    if op.startswith(('str', 'stur')):
                        write(location, size, reg(operands[0].reg))
                    else:
                        value = read(location, size)
                        put(operands[0].reg, None if value is None else int.from_bytes(value, 'little'))
                if instruction.writeback:
                    put(mem.base, location)
                continue
            _, written = instruction.regs_access()
            for number in written:
                put(number, None)
    return False
