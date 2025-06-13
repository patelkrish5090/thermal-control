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

// Alpha-Beta Filter parameters
double alpha = 0.5; // Alpha for temperature estimation (0 < alpha < 1)
double beta = 0.05;  // Beta for rate of change estimation (0 < beta < 1)
                     // Adjust alpha and beta based on your system's noise and responsiveness
double temperature_filtered = 0; 
double temperature_rate = 0;     // Estimated rate of change of temperature

double set_temperature = 50.0;
double outputPWM = 0;

int kp = 15;
int ki = 0.7;
int kd = 0;

PID myPID(&temperature_filtered, &outputPWM, &set_temperature, kp, ki, kd, DIRECT);

unsigned long last_filter_time = 0;

void setup() {
  Serial.begin(9600);

  pinMode(PWM_pin, OUTPUT);

  ledcAttach(PWM_pin, 1000, 8); // Channel, Frequency, Resolution (8-bit = 0-255)
  ledcWrite(PWM_pin, 0);

  myPID.SetMode(AUTOMATIC);
  myPID.SetOutputLimits(0, 255);

  delay(500);

  // Initialize filter with an initial reading
  temperature_read = thermocouple.readCelsius();
  if (!isnan(temperature_read)) {
    temperature_filtered = temperature_read;
    temperature_rate = 0; // Assume no initial rate of change
  }
  last_filter_time = millis();
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
      Serial.println(set_temperature);
    } else {
      Serial.println("Invalid temperature range");
    }
  }

  // Read raw temperature
  temperature_read = thermocouple.readCelsius();

  if (isnan(temperature_read)) {
    ledcWrite(PWM_pin, 0); // Turn off heater
    Serial.println("Thermocouple error");
    delay(1000);
    return;
  }

  // --- Alpha-Beta Filter Implementation ---
  unsigned long current_time = millis();
  double dt = (current_time - last_filter_time) / 1000.0; // Time difference in seconds
  last_filter_time = current_time;

  if (dt == 0) dt = 0.001; // Avoid division by zero, min dt

  // Predict step
  double predicted_temperature = temperature_filtered + (temperature_rate * dt);
  double predicted_rate = temperature_rate;

  // Update step
  double residual = temperature_read - predicted_temperature;
  temperature_filtered = predicted_temperature + (alpha * residual);
  temperature_rate = predicted_rate + (beta * residual / dt);
  // --- End of Alpha-Beta Filter Implementation ---


  // Use filtered temperature for PID control
  myPID.Compute();

  ledcWrite(PWM_pin, (int)(outputPWM));

  // Print data in CSV format: setpoint, raw_temp, filtered_temp, pwm_output, temperature_rate
  Serial.print(set_temperature);
  Serial.print(",");
  Serial.print(temperature_read, 2);    // Raw temperature reading
  Serial.print(",");
  Serial.print(temperature_filtered, 2); // Alpha-Beta filtered temperature
  Serial.print(",");
  Serial.print(outputPWM);
  Serial.print(",");
  Serial.print(temperature_rate, 2);     // Print the estimated rate of temperature change
  Serial.println();

  delay(250);
}