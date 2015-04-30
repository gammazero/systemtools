"""
Module to query system stats data.

"""
from __future__ import print_function

import subprocess
import string
import time
import os
import platform

__author__ = "Andrew Gillis"


# Seconds that stats are good before needing to be refreshed.
STATS_TTL = 60

# Values used when converting bytes into KB, MB and GB values.
KB = 1024
MB = KB*1024
GB = MB*1024


class SystemStats(object):

    def __init__(self):
        self._last_uptime_load = 0
        self._uptime = None
        self._load = None

        self._last_disk = 0
        self._disk_stats = None

        self._last_mem = 0
        self._mem_stats = None

    def __str__(self):
        """Get stats information as string."""
        st = [self.uptime_str(),
              self.disk_usage_str(),
              self.cpu_load_str(),
              self.memory_usage_str(),
              self.logical_cpu_count_str()]
        return '\n\n'.join(st)

    def uptime_str(self):
        """Return uptime string."""
        title = 'Uptime:'
        st = [title]
        st.append('-'*len(title))
        up = self.uptime()
        st.append('Up for %s days, %s hours and %s minutes'
                  % (up['days'], up['hours'], up['minutes']))
        return '\n'.join(st)

    def disk_usage_str(self):
        """Return disk usage information as string."""
        title = 'Disk Usage:'
        st = [title]
        st.append('-'*len(title))
        disks = self.disk_usage()
        for mount in disks:
            st.append('Usage for: %s' % mount)
            disk_info = disks[mount]
            for part in disk_info:
                st.append('  %s: %s' % (part, disk_info[part]))
            st.append('')
        if disks:
            st.pop()
        return '\n'.join(st)

    def cpu_load_str(self):
        """Return CPU load average information as string."""
        title = 'CPU Load Average:'
        st = [title]
        st.append('-'*len(title))
        load_stats = self.cpu_load()
        st.append('last one minute: %s' % load_stats['one'])
        st.append('last five minutes: %s' % load_stats['five'])
        st.append('last fifteen minutes: %s' % load_stats['fifteen'])
        return '\n'.join(st)

    def memory_usage_str(self):
        """Return memory usage information as string."""
        title = 'Memory usage:'
        st = [title]
        st.append('-'*len(title))
        mem_info = self.memory_usage()
        for mem_type in ('total', 'available', 'used', 'free', 'swap_total',
                         'swapped'):
            st.append('%s: %s' % (mem_type, mem_info.get(mem_type, 'n/a')))
        return '\n'.join(st)

    def logical_cpu_count_str(self):
        title = 'Logical CPU Count:'
        st = [title]
        st.append('-'*len(title))
        st.append(str(self.logical_cpu_count()))
        return '\n'.join(st)

    def uptime(self):
        """Return uptime info dictionary."""
        self._get_uptime_load()
        return self._last_uptime

    def cpu_load(self):
        """Return CPU load information dictionary."""
        self._get_uptime_load()
        return self._last_load

    def disk_usage(self):
        """Return disk usage dictionary.

        The top-level disk-usage dictionary has keys consisting of each
        mount point on the file sysem and values consisting of a dictionary of
        information pertaining to that mount point.

        Each mount point dictionary containing the following keys: partition,
        blocks, used, available, capacity.  Each value is a string describing
        the corresponding data.

        """
        now = int(time.time())
        if now - self._last_disk < STATS_TTL:
            return self._disk_stats

        proc = subprocess.Popen(('df', '-P'), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate()
        df = out.decode('utf-8').strip().split('\n')
        block_size = int(df[0].split()[1].split('-')[0])
        ds = {}
        for l in df[1:]:
            cell = l.split()
            mount = cell[5]
            used = int(cell[2]) * block_size
            avail = int(cell[3]) * block_size
            ds[mount] = {
                'partition': cell[0],
                'blocks': '%s (size=%d)' % (cell[1], block_size),
                'used': '%s (%s)' % (used, SystemStats.size_str(used)),
                'available': '%s (%s)' % (avail, SystemStats.size_str(avail)),
                'capacity': cell[4]}

        self._last_disk = now
        self._disk_stats = ds
        return ds

    def memory_usage(self):
        """Return memory usage information dictionary.

        The dictionary returned has the following keys: free, used, total,
        swapped, swap_total, available.  Each value is a string specifying the
        associated value.

        """
        now = int(time.time())
        if now - self._last_mem < STATS_TTL:
            return self._mem_stats

        if platform.system() == 'Linux':
            mem_stats = self._get_linux_mem()
        elif platform.system() == 'FreeBSD':
            mem_stats = self._get_freebsd_mem()
        else:
            na = 'n/a'
            mem_stats = {'free': na, 'used': na, 'total': na, 'swapped': na,
                         'swap_total': na, 'available': na}

        self._last_mem = now
        self._mem_stats = mem_stats
        return mem_stats

    def logical_cpu_count(self):
        cores = 0
        if platform.system() == 'Linux':
            cpu_path = '/dev/cpu'
            if os.path.exists(cpu_path):
                for dirent in os.listdir(cpu_path):
                    if dirent.isdigit():
                        cores += 1
        elif platform.system() == 'FreeBSD':
            ncpu = subprocess.check_output(
                ['sysctl', '-a', 'hw.ncpu']).decode('utf-8')
            cores = int(ncpu.split(':')[-1].strip())
        else:
            return 1
        return cores

    def _get_uptime_load(self):
        # If not enough time has elapsed, then do not update stats.
        now = int(time.time())
        if now - self._last_uptime_load < STATS_TTL:
            return

        self._last_uptime_load = now
        not_nums = string.whitespace+string.ascii_letters+string.punctuation
        uptime = subprocess.check_output('uptime').decode('utf-8')

        ut = uptime.split(',')
        days = ut[0]
        if days.find('day') == -1:
            idx = days.find('up')
            duration = days[idx + 3:]
            days = 0
        else:
            days_idx = days.find('up')
            days = days[days_idx + 3:].strip(not_nums)
            duration = ut[1]

        duration = duration.strip(not_nums)
        if ':' in duration:
            hours, minutes = duration.split(':')
        else:
            hours = 0
            minutes = duration
        self._last_uptime = {'days': int(days), 'hours': int(hours),
                             'minutes': int(minutes)}

        one, five, fifteen = uptime.strip(',').rsplit(None, 3)[-3:]
        self._last_load = {'one': float(one.rstrip(',')),
                           'five': float(five.rstrip(',')),
                           'fifteen': float(fifteen.rstrip(','))}

    def _get_linux_mem(self):
        """Get the available memory for a linux system.

        This is done by reading /proc/meminfo

        """
        meminfo = {}

        def convert_mem(label):
            mem, units = meminfo[label].split()
            if units == 'kB':
                mem = int(mem) * 1024
            elif units == 'mB':
                mem = int(mem) * 1024 * 1024
            else:
                mem = int(mem)
            return mem

        mem_free = mem_used = mem_total = mem_avail = 'n/a'
        swapped = swap_total = 'n/a'
        if os.path.exists('/proc/meminfo'):
            try:
                with open('/proc/meminfo') as file_meminfo:
                    meminfo_data = file_meminfo.read()
                for l in meminfo_data.split("\n"):
                    if ':' not in l:
                        continue
                    k, v = l.split(':', 1)
                    meminfo[k] = v.strip()

                mem_total = convert_mem('MemTotal')
                mem_free = convert_mem('MemFree')
                mem_buffers = convert_mem('Buffers')

                mem_cached = convert_mem('Cached')
                #mem_inactive = convert_mem('Inactive')
                swapped = convert_mem('SwapCached')
                swap_total = convert_mem('SwapTotal')

                # determine logical summary information
                #mem_avail = mem_inactive + mem_cached + mem_free
                mem_avail = mem_buffers + mem_cached + mem_free
                mem_used = mem_total - mem_avail

                mem_free = '%d (%s)' % (mem_free,
                                        SystemStats.size_str(mem_free))
                mem_total = '%d (%s)' % (mem_total,
                                         SystemStats.size_str(mem_total))
                mem_avail = '%d (%s)' % (mem_avail,
                                         SystemStats.size_str(mem_avail))
                mem_used = '%d (%s)' % (mem_used,
                                        SystemStats.size_str(mem_used))
                swapped = '%d (%s)' % (swapped, SystemStats.size_str(swapped))
                swap_total = '%d (%s)' % (swap_total,
                                          SystemStats.size_str(swap_total))
            except Exception:
                pass

        return {'free': mem_free, 'used': mem_used, 'total': mem_total,
                'swapped': swapped, 'swap_total': swap_total,
                'available': mem_avail}

    def _get_freebsd_mem(self):
        """Get the available memory for a FreeBSD system.

        This is done by reading information from sysctl.

        """
        mem_free = mem_used = mem_total = mem_avail = 'n/a'
        swapped = swap_total = 'n/a'
        try:
            sysctl = {}
            out = subprocess.check_output(
                ('/sbin/sysctl', '-a')).decode('utf-8').strip()
            for l in out.split('\n'):
                if ':' not in l:
                    continue
                k, v = l.split(':', 1)
                sysctl[k] = v

            def mem_rounded(mem_size):
                chip_size = 1
                chip_guess = (mem_size // 8) - 1
                while (chip_guess):
                    chip_guess >>= 1
                    chip_size <<= 1
                return ((mem_size // chip_size) + 1) * chip_size

            mem_phys = int(sysctl['hw.physmem'])
            page_size = int(sysctl['hw.pagesize'])
            mem_hw = mem_rounded(mem_phys)
            #mem_all = (int(sysctl['vm.stats.vm.v_page_count']) * page_size)
            #mem_wire = (int(sysctl['vm.stats.vm.v_wire_count']) * page_size)
            #mem_active= (int(sysctl['vm.stats.vm.v_active_count'])* page_size)
            mem_inactive = (int(sysctl['vm.stats.vm.v_inactive_count']) *
                            page_size)
            mem_cache = (int(sysctl['vm.stats.vm.v_cache_count']) * page_size)
            mem_free = (int(sysctl['vm.stats.vm.v_free_count']) * page_size)

            swap_total = int(sysctl['vm.swap_total'])
            swapped = int(sysctl['vm.stats.vm.v_swappgsout'])

            # determine logical summary information
            mem_total = mem_hw
            mem_avail = mem_inactive + mem_cache + mem_free
            mem_used = mem_total - mem_avail

            mem_free = '%d (%s)' % (mem_free, SystemStats.size_str(mem_free))
            mem_total = '%d (%s)' % (mem_total,
                                     SystemStats.size_str(mem_total))
            mem_avail = '%d (%s)' % (mem_avail,
                                     SystemStats.size_str(mem_avail))
            mem_used = '%d (%s)' % (mem_used, SystemStats.size_str(mem_used))
            swapped = '%d (%s)' % (swapped, SystemStats.size_str(swapped))
            swap_total = '%d (%s)' % (swap_total,
                                      SystemStats.size_str(swap_total))
        except Exception:
            pass

        return {'free': mem_free, 'used': mem_used, 'total': mem_total,
                'swapped': swapped, 'swap_total': swap_total,
                'available': mem_avail}

    def _get_uptime(self):
        """Get output from 'uptime' command

        If insufficient time has elapsed since last call, then return cached
        value.

        """
        now = int(time.time())
        if now - self._last_uptime >= STATS_TTL:
            self._last_uptime = now
            self._uptime = subprocess.check_output('uptime').decode('utf-8')
        return self._uptime

    @staticmethod
    def size_str(byte_size):
        if byte_size > GB:
            return str(round(float(byte_size) / GB, 1)) + 'G'
        if byte_size > MB:
            return str(round(float(byte_size) / MB, 1)) + 'M'
        if byte_size > KB:
            return str(round(float(byte_size) / KB, 1)) + 'K'
        return str(byte_size)


if __name__ == '__main__':
    # This module can be run alone to output stats info for the local system.
    print(SystemStats())
