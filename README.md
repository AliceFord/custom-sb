# Custom SweatBox

A custom sweatbox written by Alice Ford (@AliceFord)

Please note, this software is in rapid development, so may have bugs!

### Installation Instructions

1. Download / Clone repository
2. Install python dependencies with `pip install -r requirements.txt`
3. Start local FSD server
4. Start Euroscope with a view of the Gatwick airspace
5. Connect to the local FSD server as `EGKK_APP`
6. Run the software with `python main.py`
7. Enjoy!

### Usage Instructions

To use the custom SB, once loaded, click on the aircraft callsign in the window created. Then, you can type any of the following commands (exactly):

- d [FL] - Descend FL... (note currently all altitudes are flight levels for now)
- c [FL] - Climb FL...
- tl [Heading] - Turn left heading...
- tr [Heading] - Turn right heading...
- sp [Speed] - Speed...
- rond [Fix] - Resume own navigation direct fix
- pd [Fix] - Proceed direct to fix
- sq [Squawk] - Squawk...
- hold [fix] - Hold at...

- star [STAR] [Aerodrome ICAO] - [Star] arrival for [Aerodrome]
- ils [runway] - Cleared ILS runway...

- ho [ID] - Handoff to ID
