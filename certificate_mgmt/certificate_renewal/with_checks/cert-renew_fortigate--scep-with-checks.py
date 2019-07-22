#! /usr/bin/env python3
if True: # imports    
    import io
    import os
    import sys
    from netmiko import Netmiko
    from netmiko import ConnectHandler
    import datetime
    from datetime import date
    from dateutil import parser
    import time
if True: # set variables
    now = datetime.datetime.now()
    month = '{:02d}'.format(now.month)
    day = '{:02d}'.format(now.day)
    device_ip = '''+DEVICE IP HERE+'''
    device_username = '''+DEVICE UN HERE+'''
    device_password = '''+DEVICE PWD HERE+'''
    device_inside = '''+DEVICE INSIDE INTERFACE HERE+'''
    hostname = '''+DEVICE HOSTNAME HERE+'''
    domain = '''+DEVICE SUBDOMAIN HERE+''' 
    date_format = f'{now.year}{month}{day}'
    ca_ip = '''+CA IP HERE+'''
    ca_cn = '''+CA COMMON NAME HERE+'''
    cert_url = f'http://{ca_ip}/certsrv/mscep/mscep.dll'
    cert_country = '''+2-DIG COUNTRY FOR CERT HERE+'''
    cert_state = '''+STATE FOR CERT HERE+'''
    cert_city = '''CITY FOR CERT HERE+'''
    cert_org = '''ORGANIZATION FOR CERT HERE+'''
    cert_email = '''EMAIL FOR CERT HERE+'''
    todays_date = now
if True: # define find if string contains numbers function
    def hasNumbers(x):
        return any(char.isdigit() for char in x)
if True: # define unique indices function
    def unique_indices(list):
        unique_list = []

        for i in list:
            if i not in unique_list:
                unique_list.append(i)
        
        return unique_list
if True: # define unique string function
    def unique_string(s):
        unique_string_list = []

        if s not in unique_string_list:
            unique_string_list.append(s)
        
        return unique_string_list
if True: # define date normalize function
    def norm_date(n):
        normalized_date = parser.parse(n)
        yr = int(normalized_date.strftime("%Y"))
        mo = int(normalized_date.strftime("%m"))
        d = int(normalized_date.strftime("%d"))
        normalized_date = date(yr, mo, d)
        return normalized_date
if True: # create device dictionary (fortinet)
    device = {
        'host': device_ip,
        'username': device_username,
        'password': device_password,
        'device_type': 'fortinet'
    }
if True: # get device source-IP (fortinet)
    with ConnectHandler(**device) as channel:
        cmd = 'show system interface'
        output = channel.send_command(cmd)
        output_lines = output.split()
        
        for l in output_lines:
            if device_inside in l:
                start_ip_info = output_lines.index(l)
            
        ip_info = output_lines[start_ip_info:(start_ip_info + 10)]
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
if True: # get certificate names and 'valid to' dates (fortinet)
    with ConnectHandler(**device) as channel:
        cmd = 'show vpn ipsec phase1-interface'
        output = channel.send_command(cmd)
        output_lines = output.split()
        certificates = []

        for idx, val in enumerate(output_lines):
            if val == "certificate":
                cert_name = output_lines[idx + 1]
                certificates.append(cert_name)
        
        current_certs = unique_indices(certificates)

        for i in current_certs:
            i = str(i)
            cmd = f'get vpn certificate local details {i}'
            output = channel.send_command(cmd)
            output_lines = output.split()

        for l in output_lines:
            if "to:" in l:
                valid_to = output_lines.index(l)
                valid_to = output_lines[valid_to + 1]
        
        valid_to = norm_date(valid_to)
        todays_date = str(todays_date)
        todays_date = norm_date(todays_date)
        delta = valid_to - todays_date
        days_rem = delta.days

    print(f"There are {days_rem} days before these certificates expire:")
    cont = input("Continue (only 'yes' will be accepted as an affirmative)? ")
if True: # check vpn, ospf and generate certificate (fortinet)
    while cont.lower() != "yes" and "n" not in cont.lower():
        cont = input("Continue (only 'yes' will be accepted as an affirmative)? ")
    
    if cont.lower() == "yes":
        with ConnectHandler(**device) as channel:
            cmd1 = 'get vpn ipsec tunnel summary'
            output = channel.send_command(cmd1)
            output_lines = output.split()
            tunnel_status = []

            for idx, val in enumerate(output_lines):
                if "selectors" in val:
                    tun = output_lines[idx + 1]
                    tunnel_status.append(tun)
            
            for i in tunnel_status:
                if i != '1/1':
                    print("Please check VPN tunnels before renewing certificate.")
                    print("Exiting script...")
                    sys.exit()

                else:
                    print("Creating new certificate...")
                    cmd2 = f'execute vpn certificate local generate rsa {date_format} 2048 {hostname}.{domain} {cert_country} {cert_state} {cert_city} {cert_org} "" {cert_email} {hostname} {cert_url} "" {src_ip} {ca_cn}'
                    output = channel.send_command(cmd2)

            commandset = [
                'config vpn certificate local',
                f'edit {date_format}',
                'set auto-regenerate-days 30',
                'next',
                'end'
            ]

            for c in commandset:
                output = channel.send_command_timing(c)
    else:
        print("Exiting script...")
        sys.exit()
if True: # validate certificate and apply to tunnels (fortinet)
    with ConnectHandler(**device) as channel:
        cmd1 = f'show vpn certificate local {date_format}'
        output = channel.send_command(cmd1)
        output_lines = output.split()

        if len(output_lines) < 1:
            print("Cert not found. Please validate certificate was created.")
            print("Exiting script...")
            sys.exit()
        else:
            cmd2 = 'show vpn ipsec phase1-interface'
            tun_names = channel.send_command(cmd2)
            tun_names = tun_names.split()
            vpn_names = []

            for idx, val in enumerate(tun_names):
                if val == "edit":
                    tun_name = tun_names[idx + 1]
                    vpn_names.append(tun_name)

        vpn_count = len(vpn_names)   
        count = 0

        while count < vpn_count:
            for i in vpn_names:
                commandset = [
                    'config vpn ipsec phase1-interface',
                    f'edit {i}',
                    f'set certificate {date_format}',
                    'next',
                    'end'
                ] 
                for c in commandset:
                    output = channel.send_command_timing(c)
                count += 1
if True: # time sleep to allow convergence
    print("New certificate applied! Allowing time for convergence...")
    time.sleep(30)
if True: # validate config, vpn and ospf
    with ConnectHandler(**device) as channel:
        print("Validating new confguration...")
        cmd1 = 'show vpn ipsec phase1-interface'
        output = channel.send_command(cmd1)
        output_lines = output.split()
        certificates = []

        for idx, val in enumerate(output_lines):
            if val == "certificate":
                cert_name = output_lines[idx + 1]
                certificates.append(cert_name)
        
        current_certs = unique_indices(certificates)

        for i in current_certs:
            if date_format not in i:
                print("Certificate not applied to VPN. Please validate manually.")
                print("Exiting script...")
                sys.exit()

        cmd2 = 'get vpn ipsec tunnel summary'
        output = channel.send_command(cmd2)
        output_lines = output.split()
        tunnel_status = []

        for idx, val in enumerate(output_lines):
            if "selectors" in val:
                tun = output_lines[idx + 1]
                tunnel_status.append(tun)
        
        for i in tunnel_status:
            if i != '1/1':
                print("VPN tunnels down. Please validate manually.")
                print("Exiting script...")
                sys.exit()
            else:
                print("Job complete!")
                print("Remember to revoke OLD certificate on the CA!!!")
#if True: # Global test block