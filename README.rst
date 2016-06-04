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

* no retry support

* no mention of cost of blocking domain name resolution

This repo contains a minimal example avoiding these design problems.
I can pump 10K connections through it without data loss on a 1.3GHz
Macbook Air from 2013 with OS X 10.11, achieving ~1K concurrent clients.
Try how many your box can handle!

Setup
-----

Make sure to ``ulimit -n $NUMBER_OF_CONCURRENT_CONNECTIONS+100`` on the
server shell.

On the client you can experiment with any number. Low numbers will
decrease concurrency (try 100) and thus speed, high numbers increase
load, to the point of saturating CPU (try 15000), at which point no
further speedup can be achieved. Also try varying ``ulimit`` and the
number of connections you launch ``echocli`` with, observe results.
Example output of ``time python3 echocli.py 10000``::

	PID(3505781) attempting 10000 connections
	10000 tasks, 0 exceptions, 0 retries
	python3 echocli.py 10000  4.59s user 1.26s system 98% cpu 5.952 total

On OS X it's also helpful to run something like::

  sudo sysctl -w kern.maxfiles=40960
  sudo sysctl -w kern.maxfilesperproc=20480
  sudo sysctl -w net.inet.icmp.icmplim=10000

This will ensure the kernel doesn't treat your C10k attempt as
a denial-of-service attack.

Known Issues
------------

Report all remaining issues with this example on the Issues page,
please.
