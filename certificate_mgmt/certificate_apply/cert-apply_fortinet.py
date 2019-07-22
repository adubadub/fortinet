#! /usr/bin/env python3
if True: # imports    
    import io
    import os
    from netmiko import Netmiko
    from netmiko import ConnectHandler
    import datetime
if True: # set variables
    session_log = io.BytesIO()
    now = datetime.datetime.now()
    month = '{:02d}'.format(now.month)
    day = '{:02d}'.format(now.day)
    device_ip = '''+DEVICE IP HERE+'''
    username = '''+DEVICE UN HERE+'''
    password = '''+DEVICE PWD HERE+'''
    date_format = f'{now.year}{month}{day}'
if True: # create device dictionary
    device = {
        'host': device_ip,
        'username': username,
        'password': password,
        'device_type': 'fortinet',
        'session_log': session_log
    }
if True: # create command lists (fortinet)
    commandset_1 = [
        'config vpn certificate local',
        f'edit {date_format}',
        'set certificate "-----BEGIN CERTIFICATE-----'
    ]
    commandset_2 = [
        '-----END CERTIFICATE-----"',
        'next',
        'end'
    ]
if True: # open socket and add configs (fortinet)       
    with ConnectHandler(**device) as channel1:
        session = session_log.getvalue().decode()
        
        for i in commandset_1:
            channel1.send_command_timing(i)

        cer_orig = open(f'{date_format}.cer', 'r+')
        cer_orig_lines = cer_orig.readlines()
        cer_orig.close()

        with open('cer_update.txt', 'w+') as cer_conf:
            for i in cer_orig_lines:
                cer_conf.write(i)

        cer_new = open('cer_update.txt', 'r+')
        cer_lines = cer_new.readlines()
        cer_lines = [i.replace('-----BEGIN CERTIFICATE-----', '') for i in cer_lines]
        cer_lines = [i.replace('-----END CERTIFICATE-----', '') for i in cer_lines]
        cer_lines.pop()
        cer_lines.pop(0)

        for l in cer_lines:
            channel1.send_command_timing(l)

        for i in commandset_2:
            channel1.send_command_timing(i)

        cer_new.close()
if True: # write session log to temp file
    with open('temp.txt', 'w') as f:
        sensitive_words = ["''' -p '''", "password", "Password", "optional company name"]
        f.write(session)
        f.close()

    if True: # remove sensitive information from temp file and rewrite to stdout
        with open('stdout.txt', 'w') as nf:
            logs = open('temp.txt', 'r+')
            log_lines = logs.readlines()

            for line in log_lines:
                if any(words in line for words in sensitive_words):
                    nf.write('-' * 85 + '\n')
                    nf.write('REDACTED FOR SECURITY\n')
                    nf.write('-' * 85 + '\n')
                else:
                    nf.write(line)

            logs.close()
if True: # remove temp files
    os.remove('cer_update.txt')
    os.remove('temp.txt')
if True: # print 'complete' message to terminal
    print("Job complete!")