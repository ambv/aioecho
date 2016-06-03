=====================================================
A less misleading `echo` protocol example for asyncio
=====================================================

I was disappointed to see the existing echo server and client examples
for asyncio repeating the same mistakes every time.  Mistakes that will
get you in trouble when trying to do non-trivial work, namely:

* presenting code that will not work concurrently by default (which is
  the point of ``asyncio`` after all)

* conflation of concerns

  * hard-coding data within the protocol instead of letting the user
    parametrize it by default

  * exposing the event loop to the protocol, or even stopping it from
    within the protocol; this is not composable

  * needless scheduling of asynchronous post-processing, which increases
    fragility on high load

* lack of visibility into the current state of the client/server

* code that will cause ungraceful exception handling under load

This repo contains a minimal example avoiding these design problems.
I can pump 10K connections through it without data loss on a 1.3GHz
Macbook Air from 2013 with OS X 10.11, achieving ~1K concurrent clients.
Try how many your box can handle!

Report all remaining issues with this example on the Issues page,
please.
