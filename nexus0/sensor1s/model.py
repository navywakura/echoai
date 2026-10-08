"""The SENSOR-1S body: PX4's X500 with sensor elements and nothing else.

The stock x500/x500_base SDFs from the pinned image are kept byte for byte
in assets/px4_stock. The rig is derived from them by inserting one block
of <sensor> elements into base_link and renaming two references, so mass,
inertia, collisions, visuals, motors and the stock IMU are PX4's own.
"""
from pathlib import Path

from echoai.nexus0.sim3.canon import sha256_bytes

HERE = Path(__file__).resolve().parent
STOCK = HERE/'assets/px4_stock'
OUT = HERE/'assets/models'
MODEL = 'x500_sensor1s'
STOCK_SHA256 = {'x500/model.sdf': '76d8668c9c1a10348f9b7011d892203f319e5051dc8c0eb06c62e52db8e6714e',
                'x500_base/model.sdf': 'f0f04e4314eebde287eea2b0a962e31a9009f1d98470734a8137e888f78c5bf9'}
# Where PX4 mounts its own OakD-Lite on this frame: above the propeller plane.
MOUNT = '0.12 0.03 0.242 0 0 0'
BLOCK = f'''      <sensor name="sensor1s_rgb" type="camera">
        <pose>{MOUNT}</pose>
        <always_on>1</always_on>
        <update_rate>15</update_rate>
        <topic>sensor1s/rgb</topic>
        <camera>
          <horizontal_fov>1.2</horizontal_fov>
          <image><width>320</width><height>240</height><format>R8G8B8</format></image>
          <clip><near>0.1</near><far>50</far></clip>
        </camera>
      </sensor>
      <sensor name="sensor1s_depth" type="depth_camera">
        <pose>{MOUNT}</pose>
        <always_on>1</always_on>
        <update_rate>15</update_rate>
        <topic>sensor1s/depth</topic>
        <camera>
          <horizontal_fov>1.2</horizontal_fov>
          <image><width>160</width><height>120</height><format>R_FLOAT32</format></image>
          <clip><near>0.1</near><far>20</far></clip>
          <noise><type>gaussian</type><mean>0</mean><stddev>0.01</stddev></noise>
        </camera>
      </sensor>
      <sensor name="sensor1s_lidar" type="gpu_lidar">
        <pose>{MOUNT}</pose>
        <always_on>1</always_on>
        <update_rate>10</update_rate>
        <topic>sensor1s/lidar</topic>
        <lidar>
          <scan><horizontal><samples>360</samples><resolution>1</resolution>
            <min_angle>-3.14159265</min_angle><max_angle>3.12413936</max_angle></horizontal></scan>
          <range><min>0.3</min><max>30</max><resolution>0.001</resolution></range>
          <noise><type>gaussian</type><mean>0</mean><stddev>0.01</stddev></noise>
        </lidar>
      </sensor>
'''


def build():
    base = (STOCK/'x500_base/model.sdf').read_text()
    close = base.index('    </link>')                # the first link is base_link
    x500 = (STOCK/'x500/model.sdf').read_text()
    rig = (x500.replace("<model name='x500'>", f"<model name='{MODEL}'>", 1)
               .replace('<uri>model://x500_base</uri>', f'<uri>model://{MODEL}_base</uri>', 1))
    cfg = (STOCK/'x500/model.config').read_text().replace('<name>x500</name>', f'<name>{MODEL}</name>', 1)
    base_cfg = (STOCK/'x500_base/model.config').read_text().replace(
        '<name>x500_base</name>', f'<name>{MODEL}_base</name>', 1)
    return {f'{MODEL}/model.sdf': rig, f'{MODEL}/model.config': cfg,
            f'{MODEL}_base/model.sdf': base[:close] + BLOCK + base[close:],
            f'{MODEL}_base/model.config': base_cfg}


def write():
    for rel, text in build().items():
        (OUT/rel).parent.mkdir(parents=True, exist_ok=True)
        (OUT/rel).write_text(text)


def check():
    """Stock bytes are the pinned ones, and the rig is exactly their derivation."""
    stock = all(sha256_bytes((STOCK/k).read_bytes()) == v for k, v in STOCK_SHA256.items())
    derived = all((OUT/k).exists() and (OUT/k).read_text() == v for k, v in build().items())
    base = (STOCK/'x500_base/model.sdf').read_text()
    ours = (OUT/f'{MODEL}_base/model.sdf').read_text() if (OUT/f'{MODEL}_base/model.sdf').exists() else ''
    only_sensors = ours.replace(BLOCK, '', 1) == base
    return dict(ok=stock and derived and only_sensors, stock=stock, derived=derived,
                only_sensor_elements=only_sensors,
                files={k: sha256_bytes(v.encode()) for k, v in build().items()})


if __name__ == '__main__':
    write()
    print(check())
