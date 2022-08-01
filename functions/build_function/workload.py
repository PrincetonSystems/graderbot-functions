import sys
import syscalls_pb2
import json
import os
import subprocess
import shutil
import tempfile

def handle(req, syscall):
    args = req["args"]
    workflow = req["workflow"]
    context = req["context"]
    result = app_handle(args, context, syscall)
    if len(workflow) > 0:
        next_function = workflow.pop(0)
        syscall.invoke(next_function, json.dumps({
            "args": result,
            "workflow": workflow,
            "context": context
        }))
    return result

def app_handle(args, state, syscall):
    os.system("sh /usr/bin/setup-eth0.sh")
    os.system("mount -o remount,size=1G /tmp")
    class NewBlob(object):
        def __new__(cls, size=None):
            req = syscalls_pb2.Syscall(createBlob = syscalls_pb2.BlobCreate(size=size))
            syscall._send(req)
            response = syscall._recv(syscalls_pb2.BlobResponse())
            if response.success:
                instance = super(NewBlob, cls).__new__(cls)
                instance.fd = response.fd
                return instance
            else:
                return None

        def write(self, data):
            req = syscalls_pb2.Syscall(writeBlob = syscalls_pb2.BlobWrite(fd=self.fd, data=data))
            syscall._send(req)
            response = syscall._recv(syscalls_pb2.BlobResponse())
            if response.success:
                return len(data)
            else:
                return None

        def finalize(self, data):
            req = syscalls_pb2.Syscall(finalizeBlob = syscalls_pb2.BlobFinalize(fd=self.fd, data=data))
            syscall._send(req)
            response = syscall._recv(syscalls_pb2.BlobResponse())
            if response.success:
                return response.data.decode('utf-8')
            else:
                return None

    class Blob(object):
        def __new__(cls, name):
            name = name.encode('utf-8')
            req = syscalls_pb2.Syscall(openBlob = syscalls_pb2.BlobOpen(name=name))
            syscall._send(req)
            response = syscall._recv(syscalls_pb2.BlobResponse())
            if response.success:
                instance = super(Blob, cls).__new__(cls)
                instance.fd = response.fd
                instance.offset = 0
                return instance
            else:
                return None

        def read(self,size=None):
            req = syscalls_pb2.Syscall(readBlob = syscalls_pb2.BlobRead(fd=self.fd, offset=self.offset,length=size))
            syscall._send(req)
            response = syscall._recv(syscalls_pb2.BlobResponse())
            if response.success:
                self.offset += len(response.data)
                return response.data
            else:
                return None

    path = os.getenv("PATH")
    os.putenv("PATH", ":".join([path, "/srv/bin"]))

    cmd = """
    truncate -s 2G {img}
    mkfs.ext4 -F {img}
    mkdir -p {mnt}
    mount {img} {mnt}
    """

    os.system(cmd.format(img="/tmp/image.ext4", mnt="/tmp/mnt"))

    with tempfile.TemporaryDirectory() as build_dir:
        tarh = Blob(args["submission"])
        p = subprocess.Popen(["tar", "-xz", "--strip-components=1", "-C", build_dir], stdin=subprocess.PIPE)
        while True:
            data = tarh.read()
            if len(data) > 0:
                p.stdin.write(data)
            else:
                p.stdin.close()
                break

        p.wait()

        if os.path.exists(os.path.join(build_dir, "Makefile")):
            cmd = """
            make -C {build_dir}
            mv {build_dir}/out/* {mnt}/
            """
            os.system(cmd.format(img="/tmp/image.ext4", mnt="/tmp/mnt", build_dir=build_dir))
        else:
            cmd = """
            mv {build_dir}/* {mnt}/
            """
            os.system(cmd.format(img="/tmp/image.ext4", mnt="/tmp/mnt", build_dir=build_dir))

        cmd = """
        umount {mnt}
        e2fsck -y -f {img}
        resize2fs -M {img}
        """
        os.system(cmd.format(img="/tmp/image.ext4", mnt="/tmp/mnt", build_dir=build_dir))
    output = NewBlob()
    with open("/tmp/image.ext4", mode="rb") as f:
        while True:
            data = f.read()
            if len(data) > 0:
                output.write(data)
            else:
                break
    name = output.finalize(b'')
    syscall.write_key((state["meta"]["name"] + "/image").encode('utf-8'), name.encode('utf-8'))
    return { "image": state["meta"]["name"] + "/image", "out": name }
