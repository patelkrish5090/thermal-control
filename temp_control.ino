#include <SPI.h>
#include "max6675.h"
#include <PID_v1.h>

// Pin definitions for MAX6675
int thermoDO = 19;   // SO pin
int thermoCS = 4;    // CS pin
int thermoCLK = 18;  // SCK pin

int PWM_pin = 25;

MAX6675 thermocouple(thermoCLK, thermoCS, thermoDO);

double temperature_read = 0;
double set_temperature = 50.0;
double outputPWM = 0;

int kp = 20;
int ki = 1.5;
int kd = 10;

PID myPID(&temperature_read, &outputPWM, &set_temperature, kp, ki, kd, DIRECT);

void setup() {
  Serial.begin(9600);
  Serial.println("PID Temperature Control with MAX6675");

  pinMode(PWM_pin, OUTPUT);

  ledcAttach(PWM_pin, 1000, 8);
  ledcWrite(0, 0);

  myPID.SetMode(AUTOMATIC);
  myPID.SetOutputLimits(0, 255);

  delay(500);
}

void loop() {
  temperature_read = thermocouple.readCelsius();

  if (isnan(temperature_read)) {
    Serial.println("Thermocouple disconnected or error!");
    analogWrite(PWM_pin, 255); // Turn off MOSFET (inverted logic)
    delay(1000);
    return;
  }

  myPID.Compute();

  ledcWrite(PWM_pin, (int)(outputPWM));

  Serial.print("Setpoint: ");
  Serial.print(set_temperature);
  Serial.print(" C, Current: ");
  Serial.print(temperature_read);
  Serial.print(" C, PID Output: ");
  Serial.print(outputPWM);
  Serial.println();

  delay(250);
}