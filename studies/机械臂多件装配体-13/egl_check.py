import mujoco as m
model=m.MjModel.from_xml_string('<mujoco><worldbody><geom type="sphere" size=".1"/></worldbody></mujoco>')
with m.Renderer(model) as r:r.update_scene(m.MjData(model));print(r.render().shape)
