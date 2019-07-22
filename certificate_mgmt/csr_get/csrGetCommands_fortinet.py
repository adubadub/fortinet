if True: # imports    
    import datetime
if True: # set variables
    now = datetime.datetime.now()
    month = '{:02d}'.format(now.month)
    day = '{:02d}'.format(now.day)
    device_ip = '''+DEVICE IP HERE+'''
    hostname = '''+DEVICE HOSTNAME HERE+'''
    username = '''+DEVICE USERNAME HERE+''' 
    password = '''+DEVICE PASSWORD HERE+'''
    date_format = f'{now.year}{month}{day}'
    csrname = f'{hostname}_{now.year}{month}{day}.txt'
if True: # create device (fortinet) dictionary
    device = {
        'host': device_ip,
        'username': username,
        'password': password,
        'device_type': 'fortinet'
    }
if True: # create command list (fortinet)
    commands = [
        f'show full-configuration vpn certificate local {date_format}'
    ]
