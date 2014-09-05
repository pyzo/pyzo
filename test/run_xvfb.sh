#!/bin/bash

Xvfb :1 &

export DISPLAY=:1

nosetests3

killall Xvfb

