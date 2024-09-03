import datetime


def get_int(string=None):
    if string is None:
        return None
    try:
        return int(string)
    except ValueError:
        return None

def get_timestamp(time_str=None):
    if time_str is None:
        return None
    int_time = get_int(time_str)
    if int_time is not None:
        if int_time >= 0:
            return int_time
    hour = 0
    try:
        timestamp = datetime.datetime.strptime(time_str, "%M:%S")
    except ValueError:
        try:
            timestamp = datetime.datetime.strptime(time_str, "%H:%M:%S")
            hour = timestamp.hour
        except ValueError:
            return None
    return hour*3600 + timestamp.minute*60 + timestamp.second

def get_valid_resolution(allowed_resolutions, config, res_str=None):
    if res_str is None:
        return config['default_resolution']
    if res_str in allowed_resolutions:
        return res_str
    return config['default_resolution']

def merge_lists(*args):
    merged_set = set()
    for lst in args:
        merged_set.update(lst)
    return list(merged_set)
