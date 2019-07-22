#! /usr/bin/env python3
if True: # imports    
    import io
    import os
    from netmiko import Netmiko
    from netmiko import ConnectHandler
    import datetime
    import requests
    from requests_ntlm import HttpNtlmAuth
    from bs4 import BeautifulSoup
if True: # set variables
    session_log = io.BytesIO()
    now = datetime.datetime.now()
    month = '{:02d}'.format(now.month)
    day = '{:02d}'.format(now.day)
    device_ip = '''+DEVICE IP HERE+'''
    device_inside = '''+DEVICE INSIDE INT HERE+'''
    device_username = '''+DEVICE UN HERE+'''
    device_password = '''+DEVICE PWD HERE+'''
    domain = '''+DEVICE SUBDOMAIN HERE+''' 
    hostname = '''+DEVICE HOSTNAME HERE+'''
    date_format = f'{now.year}{month}{day}'
    ca_ip = '''+CA IP HERE+'''
    ca_username = '''+CA SERVICE ACCOUNT UN HERE+'''
    ca_password = '''+CA SERVICE ACCOUNT PWD HERE+'''
    ca_cn = '''+CA COMMON NAME HERE+'''
    chal_url = f'http://{ca_ip}/certsrv/mscep_admin/mscep.dll'
    cert_url = f'http://{ca_ip}/certsrv/mscep/mscep.dll'
    cert_country = '''+2-DIG COUNTRY FOR CERT HERE+'''
    cert_state = '''+STATE FOR CERT HERE+'''
    cert_city = '''CITY FOR CERT HERE+'''
    cert_org = '''ORGANIZATION FOR CERT HERE+'''
    cert_email = '''EMAIL FOR CERT HERE+'''
if True: # define find if string contains numbers function
    def hasNumbers(x):
        return any(char.isdigit() for char in x)
if True: # get challenge password
    req = requests.get(chal_url, auth=HttpNtlmAuth(ca_username, ca_password))
    html = req.content
    data = BeautifulSoup(html, 'html.parser')
    readable_data = data.prettify()
    readable_lines = readable_data.splitlines() 
    readable_lines = [i.strip(' ') for i in readable_lines]
    values = []
    
    for i in readable_lines:
        if hasNumbers(i) is True:
            values.append(i)

    for i in values:
        if '=' in i:
            values.pop(values.index(i))
        elif 'password' in i:
            values.pop(values.index(i))

    values.pop(0)
    values.pop(-1)
    
    chal_pass = values[1]
    chal_pass = str(chal_pass)    
if True: # create device dictionary (fortinet)
    device = {
        'host': device_ip,
        'username': device_username,
        'password': device_password,
        'device_type': 'fortinet',
        'session_log': session_log
    }
if True: # get device (fortinet) source-IP
    with ConnectHandler(**device) as channel:
        commandset = [
            'show system interface'
        ]

        for c in commandset:
            output = channel.send_command(c)

        output_lines = output.split()
        
        for l in output_lines:
            if device_inside in l:
                start_ip_info = output_lines.index(l)
            if "ssl.root" in l:
                end_ip_info = output_lines.index(l)
            
        ip_info = output_lines[start_ip_info:end_ip_info]
        source_ip = []
        
        for i in ip_info:
            if hasNumbers(i) is True:
                source_ip.append(i)
        
        for i in source_ip:
            if "255" in i:
                source_ip.pop(source_ip.index(i))
            if "." not in i:
                source_ip.pop(source_ip.index(i))

        src_ip = str(source_ip[0])       
if True: # deploy scep cert to device (fortinet) 
    with ConnectHandler(**device) as channel1:
        commandset_1 = [
            f'execute vpn certificate local generate rsa {date_format} 2048 {hostname}.{domain} {cert_country} {cert_state} {cert_city} "{cert_org}" "" {cert_email} {hostname} {cert_url} {chal_pass} {src_ip} "{ca_cn}"'
        ]
      
        for c in commandset_1:
            output = channel1.send_command(c)
if True: # set scep auto-regenerate-days on device (fortinet)
    with ConnectHandler(**device) as channel2:
        commandset_2 = [
            'config vpn certificate local',
            f'edit {date_format}',
            'set auto-regenerate-days 30',
            'next',
            'end'
        ]

        for c in commandset_2:
            output = channel2.send_command_timing(c)
if True: # print 'complete' message to terminal
    print("Job complete!")