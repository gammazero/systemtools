import sys

KB = 1024
MB = KB*1024
GB = MB*1024


def size_str(byte_size):
    """Truncate number to highest significant power of 2 and add suffix."""
    if byte_size > GB:
        return str(round(float(byte_size) / GB, 1)) + 'G'
    if byte_size > MB:
        return str(round(float(byte_size) / MB, 1)) + 'M'
    if byte_size > KB:
        return str(round(float(byte_size) / KB, 1)) + 'K'
    return str(byte_size)


def main():
    if len(sys.argv) < 2:
        print('Usage: python', sys.argv[0], 'bytes', file=sys.stderr)
        return 1

    print(size_str(int(sys.argv[1])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
