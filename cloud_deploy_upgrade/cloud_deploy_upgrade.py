#! /usr/bin/env python3
if True: # imports
    import json
    import subprocess
    import sys
if True: # set environment and json variables
    with open('cloud_deploy_upgrade.json') as f:
        js = json.load(f)
        device_name         = js['DEVICE_NAME']
        cloud_onprem        = js['CLOUD']
        cloud_region        = js['REGION']
        cloud_acct          = js['ACCOUNT']
if True: # get vpc name, subnet and security-group IDs
    print("Getting all existing instance details. VPC, Subnets, etc...")
    if cloud_onprem == 'AWS':
        cmd1 = f'''aws ec2 describe-tags --profile {cloud_acct} \
        --filters "Name=key,Values=Name"
        '''
        proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        output = out.decode("utf-8")
        call = output.splitlines()
        names = []
        name = []

        for idx, val in enumerate(call):
            if device_name in val:
                start_index = idx - 5
                end_index = idx + 1
                instance_verbose = call[start_index:end_index]
                for idx, val in enumerate(instance_verbose):
                    if '"instance"' in val:
                        instance_output = instance_verbose
                name_split = val.split()
                for val in name_split:
                    if device_name in val and 'ext' not in val and 'int' not in val:
                        names.append(val)

        dup_names = [n for n in names if names.count(n) > 1]
        if len(dup_names) > 0:
            for i in names:
                if i not in name:
                    name.append(i)
        else:
            name = [names[0]]
        device_name = str(name[0])
        device_name = device_name.replace('"', '')
        device_name = str(device_name)

        try:
            for val in instance_output:
                if 'i-' in val:
                    resource = val.split()
                    for val in resource:
                        if 'i-' in val:
                            resource_id = val.replace(',','').replace('"','')
        except NameError:
            print("Please confirm device name and cloud account (prod, test, etc.) and re-run script...")
            sys.exit()

        cmd2 = f'''aws ec2 describe-instances --profile {cloud_acct} \
        --instance-id {resource_id}
        '''
        proc = subprocess.Popen(cmd2, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        output = out.decode("utf-8")
        call = output.splitlines()
        interface_subnetids = {}
        interface_sgids = {}
        vpc_ids = []
        vpc_id = []

        for idx, val in enumerate(call):
            if 'DeviceIndex' in val:
                val_split = val.split()
                intdetails = ','.join(call[idx:idx + 50]).strip().replace(' ','')
                intdetails_split = intdetails.split(',')
                for newidx, newval in enumerate(val_split):
                    if 'DeviceIndex' in newval:
                        intidx = (val_split[newidx + 1]).replace(',', '')
                        interface_subnetids[f'eth{intidx}'] = 1
                        interface_sgids[f'eth{intidx}'] = 1
                        for idx2, val2 in enumerate(intdetails_split):
                            if 'SubnetId' in val2:
                                sub_split = val2.split(':')
                                subidx = (sub_split[1]).replace(',', '').replace('"', '')
                                interface_subnetids.update({f'eth{intidx}': subidx})
                            if 'GroupName' in val2:
                                sg_full = intdetails_split[idx2:idx2 + 5]
                                for idx3, val3 in enumerate(sg_full):
                                    if 'GroupId' in val3:
                                        sg_split = val3.split(':')
                                        sgidx = (sg_split[1]).replace(',', '').replace('"', '')
                                        interface_sgids.update({f'eth{intidx}': sgidx})
            if 'VpcId' in val:
                val_split = val.split(':')
                vpcid = (val_split[1]).replace(',', '').replace('"', '')
                vpc_id.append(vpcid)
        
        dup_ids = [n for n in vpc_id if vpc_ids.count(n) > 1]
        if len(dup_ids) > 0:
            for i in vpc_ids:
                if i not in vpc_id:
                    vpc_id.append(i)
        else:
            vpcid = [vpc_id[0]]
        
        vpcid = str(vpcid[0])
        vpcid = vpcid.replace('"', '').strip()
        vpcid = str(vpcid)

        cmd3 = f'''aws ec2 describe-vpcs --profile {cloud_acct} \
        --vpc-ids {vpcid}
        '''
        proc = subprocess.Popen(cmd3, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        output = out.decode("utf-8")
        call = output.splitlines()    

        for idx, val in enumerate(call):
            if 'Name' in val:
                vpcdetail = call[idx:idx + 5]
                for newval in vpcdetail:
                    if 'Value' in newval:
                        vpc_name = newval.split(':')
                        vpc = (vpc_name[1]).replace('"', '').strip()

        vpc = str(vpc)

        for key in interface_subnetids:
            if 'eth0' in key:
                external_subnet_id = interface_subnetids[key]
            elif 'eth1' in key:
                internal1_subnet_id = interface_subnetids[key]
            elif 'eth2' in key:
                internal2_subnet_id = interface_subnetids[key]
            elif 'eth3' in key and interface_subnetids.get('eth2') == None:
                internal2_subnet_id = interface_subnetids[key]
            else:
                internal2_subnet_id = 'NA'
        for key in interface_sgids:
            if 'eth0' in key:
                ext_security_group = interface_sgids[key]
            else:
                int_security_group = interface_sgids[key]
if True: # create network interfaces
    print("Creating Network Interfaces...")
    if True: # external network interface
        if True: # create new external network interface
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            create-network-interface \
            --subnet-id {external_subnet_id} \
            --groups {ext_security_group} \
            --query "NetworkInterface.NetworkInterfaceId" \
            --output text \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
            ext1intid = out.decode("utf-8").strip()
        if False: # set delete on terminate true
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            modify-network-interface-attribute \
            --network-interface-id {ext1intid} \
            DeleteOnTermination=true \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
        if True: # set interface name
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            create-tags \
            --resources {ext1intid} \
            --tags "Key=Name,Value={device_name}-ext-1" \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
        if True: # set source/destination check
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            modify-network-interface-attribute \
            --network-interface-id {ext1intid} \
            --no-source-dest-check \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
        if True: # get IP address
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            describe-network-interfaces \
            --network-interface-ids {ext1intid} \
            --query "NetworkInterfaces[*].PrivateIpAddress" \
            --output text \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
            ext1intip = out.decode("utf-8").strip()
    if True: # internal1 network interface
        if True: # create new internal1 network interface
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            create-network-interface \
            --subnet-id {internal1_subnet_id} \
            --groups {int_security_group} \
            --query "NetworkInterface.NetworkInterfaceId" \
            --output text \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
            int1intid = out.decode("utf-8").strip()
        if False: # set delete on terminate true
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            modify-network-interface-attribute \
            --network-interface-id {int1intid} \
            DeleteOnTermination=true \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
        if True: # set interface name
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            create-tags \
            --resources {int1intid} \
            --tags "Key=Name,Value={device_name}-int-1" \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
        if True: # set source/destination check
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            modify-network-interface-attribute \
            --network-interface-id {int1intid} \
            --no-source-dest-check \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
        if True: # get IP address
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            describe-network-interfaces \
            --network-interface-ids {int1intid} \
            --query "NetworkInterfaces[*].PrivateIpAddress" \
            --output text \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
            int1intip = out.decode("utf-8").strip()
    if True: # internal2 network interface
        if (internal2_subnet_id != 'NA'): # internal2 network interface
            if True: # create new internal2 network interface
                cmd1 = f'''aws ec2 --profile {cloud_acct} \
                create-network-interface \
                --subnet-id {internal2_subnet_id} \
                --groups {int_security_group} \
                --query "NetworkInterface.NetworkInterfaceId" \
                --output text \
                '''
                proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
                out, err = proc.communicate()
                int2intid = out.decode("utf-8").strip()
            if False: # set delete on terminate true
                cmd1 = f'''aws ec2 --profile {cloud_acct} \
                modify-network-interface-attribute \
                --network-interface-id {int2intid} \
                DeleteOnTermination=true \
                '''
                proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
                out, err = proc.communicate()
            if True: # set interface name
                cmd1 = f'''aws ec2 --profile {cloud_acct} \
                create-tags \
                --resources {int2intid} \
                --tags "Key=Name,Value={device_name}-int-2" \
                '''
                proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
                out, err = proc.communicate()
            if True: # set source/destination check
                cmd1 = f'''aws ec2 --profile {cloud_acct} \
                modify-network-interface-attribute \
                --network-interface-id {int2intid} \
                --no-source-dest-check \
                '''
                proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
                out, err = proc.communicate()
            if True: # get IP address
                cmd1 = f'''aws ec2 --profile {cloud_acct} \
                describe-network-interfaces \
                --network-interface-ids {int2intid} \
                --query "NetworkInterfaces[*].PrivateIpAddress" \
                --output text \
                '''
                proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
                out, err = proc.communicate()
                int2intip = out.decode("utf-8").strip()
if True: # create EIP address
    print("Creating EIP and attaching to External Interface...")
    if True: # create Elastic IP address
        cmd1 = f'''aws ec2 --profile {cloud_acct} \
        allocate-address \
        --domain vpc \
        --query "AllocationId" \
        --output text \
        '''
        proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        eip_alloid = out.decode("utf-8").strip()  
    if True: # set EIP name
        cmd1 = f'''aws ec2 --profile {cloud_acct} \
        create-tags \
        --resources {eip_alloid} \
        --tags "Key=Name,Value={device_name}-ext" \
        '''
        proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
    if True: # attach EIP to the external interface
        cmd1 = f'''aws ec2 --profile {cloud_acct} \
        associate-address \
        --allocation-id {eip_alloid} \
        --network-interface-id {ext1intid} \
        '''
        proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
if True: # set local instance variables
    instance_type = '+INSTANCE TYPE HERE+'
    instance_key = '+INSTANCE KEY HERE+'
if True: # create instance
    print("Getting appropriate AMI ID...")
    if True: # set ami id
        if '+VPC 1 NAME HERE+' in vpc.lower():
            ami_id = '+VPC 1 AMI ID HERE+' 
        if '+VPC 2 NAME HERE+' in vpc.lower():
            ami_id = '+VPC 2 AMI ID HERE+'
    print("Creating New Instance...")
    if True: # create new firewall
        if internal2_subnet_id != 'NA':
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            run-instances \
            --image-id {ami_id} \
            --count 1 \
            --instance-type {instance_type} \
            --key-name {instance_key} \
            --disable-api-termination \
            --network-interfaces "NetworkInterfaceId={ext1intid},DeviceIndex=0" "NetworkInterfaceId={int1intid},DeviceIndex=1" "NetworkInterfaceId={int2intid},DeviceIndex=2" \
            --query "Instances[*].InstanceId" \
            --output text \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
            fw_instanceid = out.decode("utf-8").strip() 
        if internal2_subnet_id == 'NA':
            cmd1 = f'''aws ec2 --profile {cloud_acct} \
            run-instances \
            --image-id {ami_id} \
            --count 1 \
            --instance-type {instance_type} \
            --key-name {instance_key} \
            --disable-api-termination \
            --network-interfaces "NetworkInterfaceId={ext1intid},DeviceIndex=0" "NetworkInterfaceId={int1intid},DeviceIndex=1" \
            --query "Instances[*].InstanceId" \
            --output text \
            '''
            proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
            out, err = proc.communicate()
            fw_instanceid = out.decode("utf-8").strip() 
    if True: # set new firewall name
        cmd1 = f'''aws ec2 --profile {cloud_acct} \
        create-tags \
        --resources {fw_instanceid} \
        --tags "Key=Name,Value={device_name}" \
        '''
        proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
if True: # get EIP and provide output
    if True: # get EIP
        cmd1 = f'''aws ec2 --profile {cloud_acct} \
        describe-instances \
        --instance-ids {fw_instanceid} \
        --query Reservations[*].Instances[*].[PublicIpAddress] \
        --output text \
        '''
        proc = subprocess.Popen(cmd1, stdout=subprocess.PIPE, shell=True)
        out, err = proc.communicate()
        eip = out.decode("utf-8").strip() 
    if True: # generate output
        print(f'''
        Firewall Instance ID: {fw_instanceid}
        Firewall Instance EIP: https://{eip}
        External 1 Network Interface: {ext1intid}
        External 1 Network Interface IP: {ext1intip}
        Internal 1 Network Interface: {int1intid}
        Internal 1 Network Interface IP: {int1intip}
        ''')
        if internal2_subnet_id != 'NA':
            print(f'''
            Internal 2 Network Interface: {int2intid}
            Internal 2 Network Interface IP: {int2intip}
            ''')
        print('''
        ###############################################################################
        ''')
        if internal2_subnet_id != 'NA':
            print(f'''
            {{
                "External1Interface": "{ext1intip}",
                "Internal1Interface": "{int1intip}",
                "Internal2Interface": "{int2intip}",
                "ElasticIPAddress":   "{eip}"
            }}
            ''')
        else:
            print(f'''
            {{
                "External1Interface": "{ext1intip}",
                "Internal1Interface": "{int1intip}",
                "Internal2Interface": "NA",
                "ElasticIPAddress":   "{eip}"
            }}
            ''')
        print('''
        ###############################################################################
        ''')
if True: # exit script
    print("Job complete. Exiting script...")
    sys.exit()