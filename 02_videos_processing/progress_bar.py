import sys
class ProgressBar:
    def progress(self,i, total, bar_len=40):
        filled = int(bar_len * i / total)
        bar = "=" * filled + "-" * (bar_len - filled)
        percent = (i / total) * 100
        sys.stdout.write(f"\r[{bar}] {percent:5.1f}%")
        sys.stdout.flush()   