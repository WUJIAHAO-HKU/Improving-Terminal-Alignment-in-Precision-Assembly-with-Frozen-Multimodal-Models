"""Illustrative five-piece batch, no model calls and no simulated outcomes."""
from policy_interface import rank_batch, choose_action

def pose(x, y=0., yaw=0.):
    return dict(x=x, y=y, yaw=yaw)

if __name__ == "__main__":
    rows = [dict(batch_id="demo", scene_id=f"D{i}", task=task, size=20., gap=1.,
                 first=pose(40.), eye_ref=pose(41.), eye_valid=True)
            for i, task in enumerate(["dshaft", "blade", "twin", "connector", "blade"])]
    ranks = rank_batch("gpt-6.2-sol", rows, "new", 4)
    print("80% allocation", ranks)
    for quota in (3, 4, 5):
        assert sum(x["measure"] for x in rank_batch("gpt-6.2-sol", rows, "new", quota).values()) == quota
    args = dict(row=rows[0], measure=True, top=pose(42.7), top_ref=pose(40.), top_valid=True)
    print("D-flat old/new", choose_action(gate="old", **args), choose_action(gate="new", **args))
    assert choose_action(gate="old", **args)["selected"] == "first"
    assert choose_action(gate="new", **args)["selected"] == "overhead"
    assert choose_action(rows[3], False, "new")["selected"] == "first"
    assert ranks["D1"]["rank"] < ranks["D4"]["rank"]

