## NOT CODE

Anyways, currently, Move Resolution is broken. 

I need to break the components down. 

A battle will have a Field, 2 BattlePokemon which pick 2 Actions.
    Every Action affects a slot of the Field. These Actions have Events associated with them. The specifics of the event come from the specific Action. 

During battle, players will pick 2 Actions. 

After receiving 2 Actions, I re-evaluate the priority bracket, taking the actions into account. SwitchingActions take priority, then we go based on priority and speed. 

Let's assume Action 1: Flamethrower is selected to go first. 

1. Check based on accuracy and target's evasion boosts and stuff to see if it lands
2. If it lands, calculate the move's damage using the formula. Create a DamageEvent for the same.
3. Check if the burn effect triggers.
4. If it does, create a StatusEvent for the same.
5. Resolve these events in that order. 

Let's assume Action 2: Close Combat is selected to go next.

1. Check based on accuracy and target's evasion boosts and stuff to see if it lands
2. If it lands, calculate the move's damage using the formula. Create a DamageEvent for the same.
3. Create a StatChangeEvent for the changes. 
4. Resolve these events in that order. 

Note: The damage calculating formula must be Slot-based, not mon based. After resolving Action 1, Action 2 will work with a halved attack stat due to the burn. After resolving actions, I must re-evaluate the turn order. 

## Next Development Steps

- Die
- Focus on the Field. It needs two sides and space for terrain, rooms, weather, tailwind etc.
- Once you have a field, focus on making decision-making for the user accessible. This UI will help.
- Once you have the UI, create the MoveSelection and Resolution code. 

