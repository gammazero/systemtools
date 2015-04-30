# py-sysutils
Python system utilities modules.

## flock

Mutex implemented as file-based lock.  This is useful for implementing a mutex shared across separate processes.

Usable as context handler, so using the with statement acquires the associated lock for the duration of the enclosed block.

## pidutil
Utility functions for working with PID files and processes on Linux/UNIX systems.

## systemstats

Query system stats data on Linux and FreeBSD system.  The stats includes the following:

- Disk use
- Memory use
- CPU use
- Logical CPU count
- Uptime information (load avarage and uptime)

Information is available as numeric values or human-readable strings for display.

## shuffle

Fast in-place random shuffle of items in list.

## escape

Excape and un-escape characters in string.
