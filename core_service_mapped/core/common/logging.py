import json, sys, time

def log(level, message, **kwargs):
    rec = {'ts': time.time(), 'level': level, 'msg': message}
    rec.update(kwargs or {})
    sys.stdout.write(json.dumps(rec, ensure_ascii=False)+'\n')
    sys.stdout.flush()
