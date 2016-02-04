# systemtools - Python system utility modules

## checktcpconn

Check or poll to see if a TCP connection can be made to a host.  This is useful when waiting for a service to become available.

## commandpath

CommandPath is a dictionary-like object that maintains a mapping of file names to the absolute file paths.  When looking up a file's path, if the absolute path of the file is not yet known, then a set of directories is searched to find the file, and the file's path is cached.  This is useful when PATH cannot be relied on and commands or other files may not be in an expected location.

## escape

Escape and un-escape characters in string.

## flock

Mutex implemented as file-based lock.  This is useful for implementing a mutex shared across separate processes.

Usable as context handler, so using the with statement acquires the associated lock for the duration of the enclosed block.

## linkidentical

Replace identical files, in directory tree, with links to one real file.

## pidutil

Utility functions for working with PID files and processes on Linux/UNIX systems.

## progressbar

The ProgressBar object calculates the number of blocks to display as the amount of progress is updated.  By default, this prints a text-based progress bar.

## rglob

Recursive glob matcher to compare directory tree against expressions and filter matching items.

## shuffle

Fast in-place random shuffle of items in list.

## syslogger

Setup logging handler to write syslog-like messages to file or to syslog.  If writing to a file, then file rotation parameters are configurable.  Log entries can optionally by written to stderr as well.  This is useful as a simplified interface to log handler configuration.

## systemstats

Query system stats data on Linux and FreeBSD system.  The stats includes the following:

- Disk use
- Memory use
- CPU use
- Logical CPU count
- Uptime information (load average and uptime)

Information is available as numeric values or human-readable strings for display.

## toposort

Topologically sort a directed acyclic graph with cycle detection.  This is useful when sorting items into dependency order, for example, when determining what order to apply updates to many items with inter-dependencies.


## userinput

This module provides different methods to prompt for user input, including menus.  It is useful when writing interactive python programs.  All methods support an optional timeout value, to limit the time waiting for user input.
