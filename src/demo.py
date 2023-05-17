# demo.py  17/05/2023  D.J.Whale
# Demonstrate the ftag file transfer, with progress updates.
#
# You can use this as a basis for your own programs, and this example
# is also a good starting point for adding in your own progress display.

#----- ACCESS THE FILE TRANSFER AGENT ------------------------------------------
# The ftag module automatically detects whether it is running on a host computer
# or on the Raspberry Pi Pico, and will make any necessary internal adjustments
# itself, without you needing to modify your main program.

import ftag

#----- PROGRESS UPDATES --------------------------------------------------------
#   This is a user-configurable function, that can send progress updates
#   anywhere, such as to a hardware display.
#   Some updates provide a 'msg' which is a string of text to display which
#   has useful update values and messages inside it. You can ignore this
#   if your display device can't display messages.
#   Other updates provide a 'value' which is a percentage complete, between
#   0 and 100. This is useful for writing to a numeric display.
#   Please make sure when running on the Raspberry Pi Pico that this function
#   is as fast as possible; it is called regularly when data arrives, and
#   spending too long inside this function will mean incoming receive packets
#   will be lost (ultimately slowing down the whole transfer process)

# The function 'signature' must exactly match the example here,
# i.e. it needs a 'msg' parameter and a 'value' parameter.
# either or both parameters might or might not be provided at various
# times throughout the transfer process.

def show_progress(msg:str or None=None, value:int or None=None):
    """Show a message or a percentage complete value"""

    # Let's assume that our display doesn't support text messages
    # so we ignore messages
    ##if msg is not None:
    ##    print(msg)

    # But let's assume that our display can display a number in the range
    # of 0..100, to show the percentage of the transfer that has completed.
    # Not all updates have a value field provided, so we must check for
    # 'None' first, and only display the number if it is provided
    if value is not None:
        print(value)

#----- USING THE FTAG MODULE FEATURES ------------------------------------------
#   This section shows how you can build the sender and receiver into your
#   own application quite simply. ftag.send() and ftag.receive() will provide
#   defaults for everything, but a useful thing to override is the progress=
#   function. See above for an example progress function.

def demo_send():
    print("sending...")
    ftag.send(progress=show_progress)
    print("done!")

def demo_receive():
    print("receiving...")
    ftag.receive(progress=show_progress)
    print("done!")

def demo_loopback():
    print("loopback")
    ftag.loopback(rx_progress=show_progress)
    print("done!")

def demo_dir():
    ftag.files()

#----- MENU SYSTEM -------------------------------------------------------------
#   This is a simple menu system that allows your user to choose different
#   features. You might choose to replace this with a different system
#   if your system is automated, or if you have hardware that provides
#   buttons and an LCD or LED display for the user to interact with.

print("FTAG - file transfer agent - demonstrator")

while True:
    rsp = input("(S)end (R)eceive (L)oopback (D)ir (Q)uit?")
    if   rsp == "": continue
    rsp = rsp.upper()
    if   rsp == 'S': demo_send()
    elif rsp == 'R': demo_receive()
    elif rsp == 'L': demo_loopback()
    elif rsp == 'D': demo_dir()
    elif rsp == 'Q': break # quit
