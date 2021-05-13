import RPi.GPIO as GPIO
# from time import sleep


class keypad():
    default_cols = [13, 6, 5]
    default_rows = [21, 20, 26, 19]
    default_keys = [[1, 2, 3], [4, 5, 6], [7, 8, 9], ["*", 0, "#"]]

    def get_key(self, key):
        keyVal = None

        # Scan rows for pressed key
        rowVal = None
        for i in range(len(self.rows)):
            tmpRead = GPIO.input(self.rows[i])
            if tmpRead == 0:
                rowVal = i
                break

        # Scan columns for pressed key
        colVal = None
        if rowVal is not None:
            for i in range(len(self.cols)):
                GPIO.output(self.cols[i], GPIO.HIGH)
                if GPIO.input(self.rows[rowVal]) == GPIO.HIGH:
                    GPIO.output(self.cols[i], GPIO.LOW)
                    colVal = i
                    break
                GPIO.output(self.cols[i], GPIO.LOW)

        # Determine pressed key, if any
        if colVal is not None:
            keyVal = self.keys[rowVal][colVal]

        if keyVal is None:
            return

        # print(keyVal)
        self.handler(keyVal)

    def setRowsAsInput(self):
        # Set all self.rows as input
        for i in range(len(self.rows)):
            GPIO.setup(self.rows[i], GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(self.rows[i],
                                  GPIO.FALLING,
                                  callback=self.get_key,
                                  bouncetime=250)

    def setColumnsAsOutput(self):
        # Set all columns as output low
        for j in range(len(self.cols)):
            GPIO.setup(self.cols[j], GPIO.OUT)
            GPIO.output(self.cols[j], GPIO.LOW)

    def __init__(self,
                 handler,
                 keys=default_keys,
                 rows=default_rows,
                 cols=default_cols):
        GPIO.setmode(GPIO.BCM)
        self.keys = keys
        self.rows = rows
        self.cols = cols
        self.handler = handler
        self.setRowsAsInput()
        self.setColumnsAsOutput()


# matrix = keypad(handler=print)

# while True:
#     pass