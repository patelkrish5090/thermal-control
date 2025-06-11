#include <SPI.h>
#include "max6675.h"
#include <PID_v1.h>

// Pin definitions for MAX6675
int thermoDO = 19;   // SO pin
int thermoCS = 4;    // CS pin
int thermoCLK = 18;  // SCK pin

// PWM pin for MOSFET driver
int PWM_pin = 25;

// Initialize MAX6675
MAX6675 thermocouple(thermoCLK, thermoCS, thermoDO);

// Temperature variables
double temperature_read = 0;
double set_temperature = 50.0;
double outputPWM = 0;

// PID constants
int kp = 20;   // Proportional gain
int ki = 1.5;   // Integral gain
int kd = 10;   // Derivative gain

// Timing variables
unsigned long previousMillis = 0;
const long interval = 250;  // Update interval in milliseconds

PID myPID(&temperature_read, &outputPWM, &set_temperature, kp, ki, kd, DIRECT);

void setup() {
  // Initialize Serial Monitor
  Serial.begin(9600);
  Serial.println("PID Temperature Control with MAX6675");

  // Configure PWM pin
  pinMode(PWM_pin, OUTPUT);

  // Optional: Set PWM frequency for ESP32 (uncomment if using ESP32)
  ledcAttach(PWM_pin, 1000, 8);
  ledcWrite(0, 0);

  // Initialize PID
  myPID.SetMode(AUTOMATIC);
  myPID.SetOutputLimits(0, 255);

  // Wait for MAX6675 chip to stabilize
  delay(500);
}

void loop() {
  unsigned long currentMillis = millis();
  
  // Only update at specified interval
  if (currentMillis - previousMillis >= interval) {
    previousMillis = currentMillis;
    
    // Read temperature from thermocouple
    temperature_read = thermocouple.readCelsius();
    
    // Check for valid temperature reading
    if (isnan(temperature_read)) {
      Serial.println("ERROR: Thermocouple disconnected!");
      ledcWrite(PWM_pin, 0);  // Turn off heating
      return;
    }

    // Compute PID output
    myPID.Compute();

    // Apply PWM output
    ledcWrite(PWM_pin, (int)outputPWM);


    // Output data in CSV format for easy parsing
    // Format: timestamp,setpoint,current_temp,pwm_output
    Serial.print(currentMillis);
    Serial.print(",");
    Serial.print(set_temperature, 2);
    Serial.print(",");
    Serial.print(temperature_read, 2);
    Serial.print(",");
    Serial.println(outputPWM, 0);
  }
  
  // Check for serial input to change setpoint
  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    double newSetpoint = input.toDouble();
    if (newSetpoint > 0 && newSetpoint < 300) {  // Safety limits
      set_temperature = newSetpoint;
      Serial.print("# Setpoint changed to: ");
      Serial.println(set_temperature);
    }
  }
}