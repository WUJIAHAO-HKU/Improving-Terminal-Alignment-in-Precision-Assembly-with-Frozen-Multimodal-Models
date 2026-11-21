"""Unexecuted fixture designs. Each row specifies a fixed base and separately grasped loose components.
A location is a column in the jig. A bridge has two interfaces straddling two columns.
The formed object is a slip-fit bench module supported by its base; no torque, bonding or electrical tests.
"""
from dataclasses import dataclass
@dataclass(frozen=True)
class Component:
    label:str
    profile:str
    column:str
    thickness:int
    after:tuple=()
def c(name,profile,column,thick,*parents):return Component(name,profile,column,thick,parents)
RECIPES={
'01 Spacer collar and keeper':[c('spacer','round','M',6),c('keeper','round','M',4,'spacer')],
'02 Keyed hub and thrust washer':[c('hub','dflat','M',6),c('washer','round','M',4,'hub')],
'03 Blade guide and shim':[c('shim','slot','M',4),c('guide','slot','M',6,'shim')],
'04 Two-pin carrier and cover':[c('carrier','double','M',6),c('cover','double','M',4,'carrier')],
'05 Stepped shaft pack':[c('lower bush','round','M',6),c('shim','round','M',4,'lower bush'),c('upper bush','round','M',6,'shim')],
'06 Indexed cam pack':[c('cam plate','dflat','M',5),c('distance washer','round','M',4,'cam plate'),c('index plate','dflat','M',5,'distance washer')],
'07 Blade clamp sandwich':[c('backing','slot','M',5),c('wear plate','slot','M',4,'backing'),c('cap','slot','M',5,'wear plate')],
'08 Dowel-mounted shim cassette':[c('tray','double','M',5),c('height shim','double','M',4,'tray'),c('lid','double','M',5,'height shim')],
'09 Bridged sleeve pair':[c('left bush','round','L',6),c('right bush','round','R',6),c('tie plate','bridge','LR',4,'left bush','right bush')],
'10 Keyed and plain bearing retainer':[c('indexed bush','dflat','L',6),c('plain bush','round','R',6),c('keeper','bridge','LR',4,'indexed bush','plain bush')],
'11 Paired blade guide block':[c('left insert','slot','L',6),c('right insert','slot','R',6),c('guide cap','bridge','LR',5,'left insert','right insert')],
'12 Raised two-post cover':[c('left foot','round','L',4),c('left riser','round','L',4,'left foot'),c('right riser','round','R',8),c('roof','bridge','LR',4,'left riser','right riser')],
'13 Stepped guide clamp':[c('left index','dflat','L',5),c('right guide','slot','R',5),c('clamp','bridge','LR',4,'left index','right guide'),c('left retainer','dflat','L',4,'clamp')],
'14 Two-post equalizer':[c('left collar','round','L',4),c('right collar','round','R',4),c('lower bar','bridge','LR',4,'left collar','right collar'),c('upper bar','bridge','LR',5,'lower bar')],
'15 Split retainer yoke':[c('crossbar','bridge','LR',4),c('left spacer','round','L',6,'crossbar'),c('right spacer','dflat','R',6,'crossbar'),c('top yoke','bridge','LR',4,'left spacer','right spacer')],
'16 Mixed shim height compensator':[c('left washer','dflat','L',4),c('left sleeve','dflat','L',4,'left washer'),c('right blade block','slot','R',8),c('cap','bridge','LR',4,'left sleeve','right blade block'),c('right shim','slot','R',4,'cap')],
'17 Twin post thrust cartridge':[c('lower yoke','bridge','LR',4),c('left race','round','L',4,'lower yoke'),c('right race','round','R',4,'lower yoke'),c('upper yoke','bridge','LR',4,'left race','right race'),c('left stop','round','L',4,'upper yoke')],
'18 Staggered indexing frame':[c('left register','dflat','L',6),c('right foot','round','R',4),c('right shim','round','R',2,'right foot'),c('middle frame','bridge','LR',4,'left register','right shim'),c('left cap','dflat','L',4,'middle frame'),c('right cap','round','R',4,'middle frame')],
'19 Double-deck blade cage':[c('lower frame','bridge','LR',4),c('left slide','slot','L',4,'lower frame'),c('right slide','slot','R',4,'lower frame'),c('middle frame','bridge','LR',4,'left slide','right slide'),c('left guide','slot','L',4,'middle frame'),c('right guide','slot','R',4,'middle frame'),c('roof','bridge','LR',4,'left guide','right guide')],
'20 Mixed-profile bridge stack':[c('alignment baseplate','bridge','LR',4),c('left index','dflat','L',4,'alignment baseplate'),c('right guide','slot','R',4,'alignment baseplate'),c('transfer plate','bridge','LR',4,'left index','right guide'),c('left washer','round','L',4,'transfer plate'),c('right guide cap','slot','R',4,'transfer plate'),c('top plate','bridge','LR',4,'left washer','right guide cap')],
}
if __name__=='__main__':
    for k,v in RECIPES.items():
        seen=set()
        for x in v:
            assert set(x.after)<=seen and x.label not in seen;seen.add(x.label)
        print(k,len(v)+1)

