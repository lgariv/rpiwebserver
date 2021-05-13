'''
    Raspberry Pi GPIO Status and Control
'''
import RPi.GPIO as GPIO
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import sys
import smbus
import time
from keypad import keypad
from multiprocessing import Process

app = Flask('__main__')

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

#define actuators GPIOs
ledBlu = 17
ledGrn = 27
ledRed = 22
fan = 23
doorin = 16
doorout = 12

#initialize GPIO status variables
ledRedSts = 0
ledBluSts = 0
ledGrnSts = 0
fanSts = 0

# Define pins as output/input
GPIO.setup(ledRed, GPIO.OUT)
GPIO.setup(ledBlu, GPIO.OUT)
GPIO.setup(ledGrn, GPIO.OUT)
GPIO.setup(fan, GPIO.OUT)
GPIO.setup(doorin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(doorout, GPIO.OUT)
GPIO.output(doorout, GPIO.HIGH)


def get_temp():
    bus = smbus.SMBus(1)
    raw = bus.read_word_data(address, 0) & 0xFFFF
    raw = ((raw << 8) & 0xFF00) + (raw >> 8)
    current_temp = (raw / 32.0) / 8.0
    return current_temp


f = open("passcode.txt", "r+")
passcode = f.read()
current_code = []
set_new_passcode = False

ignore_sensor = False
time.sleep(0.01)
hacked = False if GPIO.input(doorin) == GPIO.HIGH else True


def passcode_is_correct():
    '''do something'''
    # print("PASSCODE IS CORRECT")
    global ignore_sensor, correct_passcode_time, current_code
    ignore_sensor = True
    for _ in range(3):
        GPIO.output(ledBlu, GPIO.HIGH)
        time.sleep(1 / 3)
        GPIO.output(ledBlu, GPIO.LOW)
        time.sleep(1 / 3)
    current_code = []


def passcode_is_incorrect():
    '''do something'''
    global current_code
    for _ in range(3):
        GPIO.output(ledRed, GPIO.HIGH)
        time.sleep(1 / 3)
        GPIO.output(ledRed, GPIO.LOW)
        time.sleep(1 / 3)
    current_code = []


def get_key(pressed_key):
    pressed_key = str(pressed_key)
    GPIO.output(ledGrn, GPIO.HIGH)
    time.sleep(0.05)
    GPIO.output(ledGrn, GPIO.LOW)
    global set_new_passcode, current_code, passcode
    if pressed_key is "*":
        if len(current_code) < 2:
            current_code.append(pressed_key)
        elif "".join(current_code) == "**":
            GPIO.output(ledRed, GPIO.HIGH)
            current_code = []
            set_new_passcode = True
    elif set_new_passcode:
        if pressed_key is "#":
            passcode = "".join(current_code)
            f.seek(0)
            f.truncate()
            f.write(passcode)
            GPIO.output(ledRed, GPIO.LOW)
            set_new_passcode = False
            current_code = []
        else:
            current_code.append(pressed_key)
    elif len(current_code) < len(passcode):
        # if less than 4 enough numbers entered
        if pressed_key != passcode[len(current_code)]:
            # if passcode until now doesn't match
            passcode_is_incorrect()
        else:
            # if it does match, add to list
            current_code.append(pressed_key)
    elif pressed_key == "#" and "".join(current_code) == passcode:
        # if "#" is pressed and current passcode match our passcode
        passcode_is_correct()
    else:
        passcode_is_incorrect()


# keypad
keypad(handler=get_key)  # perform get_key() function on keypress.

try:
    # turn  OFF, turns off fan
    GPIO.output(ledRed, GPIO.LOW)
    GPIO.output(ledBlu, GPIO.LOW)
    GPIO.output(ledGrn, GPIO.LOW)
    GPIO.output(fan, GPIO.LOW)

    # By default the address of LM75A is set to 0x48
    # aka A0, A1, and A2 are set to GND (0v).
    address = 0x48

    # Check if another address has been specified
    if 1 < len(sys.argv):
        address = int(sys.argv[1], 16)

    # Read I2C data and calculate temperature
    temperature = get_temp()

    # Print temperature
    print('Temperature: {0:0.2f} *celsius'.format(temperature))

    def fan_on_if_too_hot():
        '''
        check temprature every 0.1 seconds;
        if temprature is 30 or above, turn on the fan.
        if below 30, turn it off.
        '''
        while True:
            time.sleep(0.1)
            current_temp = get_temp()
            if current_temp < 30:
                # print("TURN FAN OFF")
                if GPIO.input(fan) == GPIO.HIGH:
                    GPIO.output(fan, GPIO.LOW)
            if current_temp >= 30:
                # print("TURN FAN ON")
                if GPIO.input(fan) == GPIO.LOW:
                    GPIO.output(fan, GPIO.HIGH)

    t = Process(target=fan_on_if_too_hot, args=())
    t.start()

    def check_door(key):
        global ignore_sensor, hacked, correct_passcode_time
        time.sleep(0.01)
        inp = GPIO.input(doorin)
        if inp == GPIO.HIGH:
            '''CLOSED'''
            hacked = False
        elif inp == GPIO.LOW:
            '''OPEN'''
            hacked = False if ignore_sensor else True
        ignore_sensor = False

    GPIO.add_event_detect(doorin,
                          GPIO.BOTH,
                          callback=check_door,
                          bouncetime=10)

    @app.route("/")
    def index():
        # Read Sensors Status
        ledRedSts = GPIO.input(ledRed)
        ledBluSts = GPIO.input(ledBlu)
        ledGrnSts = GPIO.input(ledGrn)
        fanSts = GPIO.input(fan)

        # read temp
        Temp = '{0:0.2f} *celsius'.format(get_temp())
        localtime = time.asctime(time.localtime(time.time()))

        templateData = {
            'title': 'Welcome to NOTZ Secret Server',
            'warning': 'אזהרה! בן אדם לא מזוהה נכנס לחדר',
            'ledRed': ledRedSts,
            'ledBlu': ledBluSts,
            'ledGrn': ledGrnSts,
            'T': Temp,
            'time': localtime,
            'ventilator': fanSts,
            'hacked': int(hacked),
        }
        return render_template('indexTwo.html', **templateData)

    @app.route("/<deviceName>/<action>")
    def action(deviceName, action):
        if deviceName == 'ledRed':
            actuator = ledRed
        if deviceName == 'ledBlu':
            actuator = ledBlu
        if deviceName == 'ledGrn':
            actuator = ledGrn
        if deviceName == 'ventilator':
            actuator = fan

        if action == "on":
            GPIO.output(actuator, GPIO.HIGH)
        if action == "off":
            GPIO.output(actuator, GPIO.LOW)

        # read temp
        Temp = '{0:0.2f} *celsius'.format(get_temp())
        localtime = time.asctime(time.localtime(time.time()))

        ledRedSts = GPIO.input(ledRed)
        ledBluSts = GPIO.input(ledBlu)
        ledGrnSts = GPIO.input(ledGrn)
        fanSts = GPIO.input(fan)

        templateData = {
            'title': 'Welcome to NOTZ Secret Server',
            'ledRed': ledRedSts,
            'ledBlu': ledBluSts,
            'ledGrn': ledGrnSts,
            'T': Temp,
            'time': localtime,
            'ventilator': fanSts,
            'hacked': int(hacked),
        }
        return render_template('indexTwo.html', **templateData)

    # socketio = SocketIO(app)

    @app.route('/background_process')
    def background_process():
        Temp = '{0:0.2f} *celsius'.format(get_temp())
        localtime = time.asctime(time.localtime(time.time()))
        data = jsonify(
            title='Welcome to NOTZ Secret Server',
            ledRed=ledRedSts,
            ledBlu=ledBluSts,
            ledGrn=ledGrnSts,
            T=Temp,
            time=localtime,
            ventilator=fanSts,
            hacked=int(hacked),
        )
        return data

    # @app.route('/', methods=['POST'])
    # def stuff():
    #     temperature = get_temp()

    #     Temp = '{0:0.2f} *celsius'.format(temperature)
    #     localtime = time.asctime(time.localtime(time.time()))

    #     print(Temp)
    #     data = jsonify(
    #         # templateData = {
    #         title='Welcome to NOTZ Secret Server',
    #         ledRed=ledRedSts,
    #         ledBlu=ledBluSts,
    #         ledGrn=ledGrnSts,
    #         T=Temp,
    #         time=localtime,
    #         ventilator=fanSts,
    #         # }
    #     )
    #     return data

    if __name__ == "__main__":
        app.run(host='192.168.1.161',
                port=8080,
                debug=False,
                use_reloader=False)
        # socketio.run(app, host='0.0.0.0', port=80, debug=True)
finally:
    f.close()
    GPIO.cleanup()
