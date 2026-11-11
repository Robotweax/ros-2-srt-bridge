"""Canonical logical sensor fields; matches source_trace.hpp, excludes CDR padding."""
import hashlib
import struct


def canonical(message, route):
    data = bytearray(struct.pack('<IiI', route, message.header.stamp.sec, message.header.stamp.nanosec))
    if not 0 <= message.header.stamp.nanosec < 1_000_000_000:
        raise ValueError('invalid stamp')

    def text(value):
        encoded = value.encode('utf-8')
        if len(encoded) > 64:
            raise ValueError('oversize string')
        data.extend(struct.pack('<I', len(encoded)))
        data.extend(encoded)

    def numbers(values):
        data.extend(struct.pack('<' + 'd' * len(values), *values))

    def vector(value):
        numbers((value.x, value.y, value.z))

    text(message.header.frame_id)
    if route == 1:
        vector(message.orientation)
        numbers((message.orientation.w,))
        numbers(message.orientation_covariance)
        vector(message.angular_velocity)
        numbers(message.angular_velocity_covariance)
        vector(message.linear_acceleration)
        numbers(message.linear_acceleration_covariance)
    elif route == 2:
        if len(message.name) > 6:
            raise ValueError('oversize names')
        data.extend(struct.pack('<I', len(message.name)))
        for name in message.name:
            text(name)
        for values in (message.position, message.velocity, message.effort):
            if len(values) not in (0, len(message.name)):
                raise ValueError('mismatched joint array')
            data.extend(struct.pack('<I', len(values)))
            numbers(values)
    else:
        raise ValueError('unknown source route')
    if len(data) > 928:
        raise ValueError('oversize payload')
    return bytes(data)


def fingerprint(message, route):
    return hashlib.sha256(canonical(message, route)).hexdigest()
