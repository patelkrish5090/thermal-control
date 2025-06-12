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
  Serial.println("Enter temperature setpoint in Celsius (e.g., 50.0):");

  pinMode(PWM_pin, OUTPUT);

  ledcAttach(PWM_pin, 1000, 8);
  ledcWrite(0, 0);

  myPID.SetMode(AUTOMATIC);
  myPID.SetOutputLimits(0, 255);

  delay(500);
}

void loop() {
  // Check for Serial input to set temperature
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim(); // Remove whitespace
    double new_setpoint = input.toDouble();
    
    // Validate input (ensure it's a reasonable temperature)
    if (new_setpoint > 0 && new_setpoint < 1000) { // Adjust range as needed
      set_temperature = new_setpoint;
      Serial.print("New setpoint: ");
      Serial.print(set_temperature);
      Serial.println(" C");
    } else {
      Serial.println("Invalid setpoint! Enter a number between 0 and 1000.");
    }
  }

  temperature_read = thermocouple.readCelsius();

  if (isnan(temperature_read)) {
    Serial.println("Thermocouple disconnected or error!");
    analogWrite(PWM_pin, 255); // Turn off MOSFET (inverted logic)
    delay(1000);
    return;
  }

  myPID.Compute();

  ledcWrite(PWM_pin, (int)(outputPWM));

  Serial.print(set_temperature);
  Serial.print(",");
  Serial.print(temperature_read);
  Serial.print(",");
  Serial.print(outputPWM);
  Serial.println();

  delay(250);
}