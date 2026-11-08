"""Independently encoded minimal RTPS DATA/PL-CDR advertisement for decoder QA.

Synthetic syntax fixture only; not complete DDS participant discovery or delivery.
"""
import struct
from pathlib import Path

PREFIX=bytes.fromhex('010f'+'01'*10)
ENDPOINT=PREFIX+bytes.fromhex('00000103')
TOPIC='rt/dds/commands/operator_hello'


def write_capture(path):
    def parameter(id,value):
        value+=bytes((-len(value))%4)
        return struct.pack('<HH',id,len(value))+value
    topic=TOPIC.encode()+b'\0'
    parameters=parameter(0x5,struct.pack('<I',len(topic))+topic)+parameter(0x5a,ENDPOINT)+struct.pack('<HH',1,0)
    body=struct.pack('<HH',0,16)+bytes(4)+bytes.fromhex('000003c2')+struct.pack('<iI',0,1)+bytes.fromhex('00030000')+parameters
    payload=b'RTPS'+bytes.fromhex('0203010f')+PREFIX+struct.pack('<BBH',0x15,5,len(body))+body
    udp=struct.pack('!HHHH',22410,22412,len(payload)+8,0)+payload
    ip=bytearray(struct.pack('!BBHHHBBH4s4s',0x45,0,20+len(udp),1,0,64,17,0,bytes([10,0,0,1]),bytes([10,0,0,2])))
    total=sum(struct.unpack('!10H',ip));total=(total&0xffff)+(total>>16);total=(total&0xffff)+(total>>16)
    struct.pack_into('!H',ip,10,(~total)&0xffff)
    frame=bytes.fromhex('0202020202020101010101010800')+ip+udp
    Path(path).write_bytes(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1)+struct.pack('<IIII',1,0,len(frame),len(frame))+frame)
