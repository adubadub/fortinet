#! /usr/bin/env python3
if True: # imports
    import io
    import os
    from netmiko import Netmiko
    from netmiko import ConnectHandler
    import csrGetCommands_fortinet
if True: # set variables
    session_log = io.BytesIO()
    un = csrGetCommands_fortinet.username
    pwd = csrGetCommands_fortinet.password
    dev = csrGetCommands_fortinet.device
    hn = csrGetCommands_fortinet.hostname
    fname = csrGetCommands_fortinet.csrname
if True: # update device dictionary with session log variable (for logging session)
    dev.update({'session_log': session_log})
if True: # define ssh function (fortinet)
    def ssh_socket(cmd):
        with ConnectHandler(**dev) as channel:
            output = channel.send_command_timing(cmd, strip_command=False, strip_prompt=False)
            
            with open("show_file.txt", 'w') as f:
                f.write(output)
                f.close()

            show = open('show_file.txt', 'r+')
            show_lines = show.readlines()
            show_lines = [i.replace('"', '') for i in show_lines]
            show_lines = [i.replace('        set csr ', '') for i in show_lines]

            for i in show_lines:
                if '-----BEGIN CERTIFICATE REQUEST' in i:
                    start_csr_index = show_lines.index(i)
                if 'END CERTIFICATE REQUEST-----' in i:
                    end_csr_index = show_lines.index(i)

            csr_list = show_lines[start_csr_index:(end_csr_index + 1)]

            with open(f'{fname}', 'w') as csr:    
                for i in csr_list:
                    csr.write(i)

            show.close()
if True: # call csrGetCommands_fortinet py for command list and then call ssh function with commands (and log)
    for line in csrGetCommands_fortinet.commands:
        line = str(line)
        ssh_socket(line)
        session = session_log.getvalue().decode()
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
    os.remove('show_file.txt')
    os.remove('temp.txt')
if True: # print 'complete' message to terminal
    print("Job complete!")