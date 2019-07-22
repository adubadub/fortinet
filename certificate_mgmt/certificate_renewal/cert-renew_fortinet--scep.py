#! /usr/bin/env python3
if True: # imports    
    import io
    import os
    import sys
    from netmiko import Netmiko, ConnectHandler
    import datetime
    from datetime import date
    from dateutil import parser
    import time
    import json
if True: # set json variables
    with open('cert-renew_fortinet--scep.json') as f:
        js = json.load(f)
        hostname            = js['HOSTNAME']
        domain              = js['DEVICE_DOMAIN']
        device_ip           = js['DEVICE_IP']
        device_username     = js['DEVICE_UN']
        device_password     = js['DEVICE_PWD']
        device_inside       = js['DEVICE_INSIDE_INT']
        ca_ip               = js['CA_IP']
        ca_cn               = js['CA_CN'] # CA common name
        cert_country        = js['CERT_COUNTRY']
        cert_state          = js['CERT_STATE']
        cert_city           = js['CERT_CITY']
        cert_org            = js['CERT_ORG']
        cert_email          = js['CERT_EMAIL']
if True: # set local variables
    now = datetime.datetime.now()
    month = '{:02d}'.format(now.month)
    day = '{:02d}'.format(now.day)
    date_format = f'{now.year}{month}{day}'
    cert_url = f'http://{ca_ip}/certsrv/mscep/mscep.dll'
    todays_date = now
if True: # define functions
    def hasNumbers(x):
        return any(char.isdigit() for char in x)
    # define unique indices function
    def unique_indices(list):
            unique_list = []

            for i in list:
                if i not in unique_list:
                    unique_list.append(i)
            
            return unique_list
    # define unique string function
    def unique_string(s):
            unique_string_list = []

            if s not in unique_string_list:
                unique_string_list.append(s)
            
            return unique_string_list
    # define date normalize function
    def norm_date(n):
        normalized_date = parser.parse(n)
        yr = int(normalized_date.strftime("%Y"))
        mo = int(normalized_date.strftime("%m"))
        d = int(normalized_date.strftime("%d"))
        normalized_date = date(yr, mo, d)
        return normalized_date
    # define cert gen and apply function
    def cert_gen(host, src):
        with ConnectHandler(**device) as channel:
            try:
                cmd1 = f'execute vpn certificate local generate rsa {host} 2048 {hostname}.{domain} {cert_country} {cert_state} {cert_city} "{cert_org}" "" {cert_email} {hostname} {cert_url} "" {src} "{ca_cn}"'
                channel.send_command(cmd1)

                commandset1 = [
                    'config vpn certificate local',
                    f'edit {host}',
                    'set auto-regenerate-days 30',
                    'set auto-regenerate-days-warning 20',
                    'next',
                    'end'
                ]

                for c in commandset1:
                    channel.send_command_timing(c)
            except OSError:
                print('Certificate with that name already exists. Please check SCEP status manually.')
                print('Exiting script...')
                sys.exit()

            # apply new certificate to tunnels
            print("Applying new certificate to tunnels...")
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
                    commandset2 = [
                        'config vpn ipsec phase1-interface',
                        f'edit {i}',
                        f'set certificate {host}',
                        'next',
                        'end'
                    ] 

                    for c in commandset2:
                        channel.send_command_timing(c)
                    count += 1

            print(f'Certificate name is: {host}')
            channel.disconnect()
if True: # define device dictionary
    device = {
        'host': device_ip,
        'username': device_username,
        'password': device_password,
        'device_type': 'fortinet'
    }
if True: # get inside interface IP, check existing cert expiry date, generate cert and apply to tunnels
    with ConnectHandler(**device) as channel:
        print('Getting inside interface IP...')
        cmd1 = 'show system interface'
        output = channel.send_command(cmd1)
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

        print('Checking existing certificate expiration date...')
        cmd2 = 'show vpn ipsec phase1-interface'
        output = channel.send_command(cmd2)
        output_lines = output.split()
        certificates = []

        for idx, val in enumerate(output_lines):
            if val == "certificate":
                cert_name = output_lines[idx + 1]
                certificates.append(cert_name)
        
        current_certs = unique_indices(certificates)

        for i in current_certs:            
            i = str(i)
            cmd3 = f'get vpn certificate local details {i}'
            output = channel.send_command(cmd3)
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

        if days_rem > 30:
            print(f"There are {days_rem} remaining before certificate expiration.")
            print("Exiting script...")
            sys.exit()
        
        # create new certificate
        cmd4 = 'get vpn certificate local'
        output = channel.send_command(cmd4)
        output_lines = output.split()

        if hostname in str(output_lines[:]):
            hostnew = f'{hostname}_{date_format}'
            print("Creating new certificate...")
            cert_gen(hostnew, src_ip)
            channel.disconnect()
        else:
            print("Creating new certificate...")
            cert_gen(hostname, src_ip)
            channel.disconnect()
if True: # validate certificate was applied to tunnels
    print("Validating new confguration...")
    time.sleep(21)
    try:
        with ConnectHandler(**device) as channel:
            cmd = 'show vpn ipsec phase1-interface'
            output = channel.send_command_timing(cmd)
            output_lines = output.split()
            certificates = []

            for idx, val in enumerate(output_lines):
                if val == "certificate":
                    cert_name = output_lines[idx + 1]
                    certificates.append(cert_name)
            
            current_certs = unique_indices(certificates)

            for i in current_certs:
                if hostname not in i:
                    print("Certificate not applied to VPN. Please validate manually.")
                    print("Exiting script...")
                    channel.disconnect()
                    sys.exit()
                else:
                    print("Job complete!")
                    print("Remember to revoke the OLD certificate on the CA!!!")
                    channel.disconnect()
                    sys.exit()
    except (OSError, EOFError, ValueError, KeyboardInterrupt) as error:
        print(f'Re-connection to device timed out. ({error}).')
        print('Please validate configuration manually.')
        sys.exit()