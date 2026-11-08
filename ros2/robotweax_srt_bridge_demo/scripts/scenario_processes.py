"""Owned scenario child shutdown with explicit evidence; never hide abnormal exits."""
import signal
import subprocess
import time


def stop_children(processes, wait_seconds=5):
    rows=[]
    for process,name,log in reversed(processes):
        row=dict(name=name,pid=process.pid,begin_ns=time.monotonic_ns(),initial_returncode=None,signal_sent=False,forced_kill=False,returncode=None,error=None)
        try:
            row['initial_returncode']=process.poll()
            if row['initial_returncode'] is not None:
                row['error']='child exited before controlled shutdown'
            else:
                row['signal_begin_ns']=time.monotonic_ns()
                process.send_signal(signal.SIGINT);row['signal_sent']=True
                row['signal_end_ns']=time.monotonic_ns()
                try:process.wait(timeout=wait_seconds)
                except subprocess.TimeoutExpired:
                    row['error']='child exceeded shutdown deadline';row['forced_kill']=True
                    process.kill();process.wait(timeout=wait_seconds)
            row['returncode']=process.poll()
        except Exception as error:
            row['error']=type(error).__name__+': '+str(error)
            if process.poll() is None:
                row['forced_kill']=True
                try:process.kill();process.wait(timeout=wait_seconds)
                except Exception as cleanup_error:row['cleanup_error']=str(cleanup_error)
            row['returncode']=process.poll()
        finally:
            log.close();row['end_ns']=time.monotonic_ns()
        row['passed']=row['initial_returncode'] is None and row['signal_sent'] and not row['forced_kill'] and row['returncode']==0 and row['error'] is None
        rows.append(row)
    return dict(passed=all(row['passed'] for row in rows),children=rows,scope='owned child processes only; explicit pre-signal status, SIGINT bracket, exit code and forced-kill outcome; not internal crash-cause attribution')
