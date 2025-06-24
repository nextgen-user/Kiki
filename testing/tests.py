import pexpect
Parent=pexpect.spawn('bash')
import time
def run(cmd, timeout_sec,forever_cmd):
    global Parent
    if forever_cmd == 'true':
        Parent.close()
        Parent = pexpect.spawn("bash")
        command="cd /home/pi/emo_v3/kiki-2025-03-06/codesandbox && "+cmd

        Parent.sendline(command)
        Parent.readline().decode()
        return str(Parent.readline().decode())    
    t=time.time()
    child = pexpect.spawn("bash")
    output=""
    command="cd /home/pi/emo_v3/kiki-2025-03-06/codesandbox && "+cmd

    child.sendline('PROMPT_COMMAND="echo END"')
    child.readline().decode()
    child.readline().decode()

    child.sendline(command)
    count=0

    while (not child.eof() ) and (time.time()-t<timeout_sec):
        x=child.readline().decode()
        output=output+x
        print(x)
        if "END" in x :
            output=output.replace("END","")
            count+=1
            if count>1:
                child.close()
                break
        if "true" in forever_cmd:
            break
    return output

x=run("ls",timeout_sec=300,forever_cmd="false")
print("output",x,"done")