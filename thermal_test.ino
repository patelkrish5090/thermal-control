#include <SPI.h>
#include "max6675.h"
#include <PID_v1.h>

// MAX6675 Thermocouple pins
#define thermoDO   19  // SO pin (GPIO 19)
#define thermoCS   4   // CS pin (GPIO 4) 
#define thermoCLK  18  // SCK pin (GPIO 18)

// MOSFET control pin
#define HEATER_PIN 25  // PWM pin (GPIO 25)

// Create MAX6675 object
MAX6675 thermocouple(thermoCLK, thermoCS, thermoDO);

// PID variables
double setpoint = 40.0;  // Target temperature in Celsius
double input, output;

// PID tuning parameters
double kp = 2.0, ki = 5.0, kd = 1.0;

// Create PID object
PID myPID(&input, &output, &setpoint, kp, ki, kd, DIRECT);

// PWM settings
const int freq = 5000;
const int pwmChannel = 0;
const int resolution = 8;  // 8-bit resolution (0-255)

// Timing for display
unsigned long lastPrint = 0;
const unsigned long printInterval = 1000;  // Print every 1 second

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 Temperature Control with PID_v1 Library");
  
  // Initialize PWM
  ledcAttach(HEATER_PIN, freq, resolution);
  ledcWrite(pwmChannel, 0); 
  
  // Initialize PID
  myPID.SetMode(AUTOMATIC);
  myPID.SetOutputLimits(0, 255);  // PWM range
  myPID.SetSampleTime(1000);      // 1 second sample time
  
  // Wait for MAX6675 to stabilize
  delay(500);
  
  Serial.println("Time(s)\tTemp(°C)\tSetpoint(°C)\tPWM\tError(°C)");
  Serial.println("-------\t-------\t-----------\t---\t--------");
}

void loop() {
  // Read temperature from MAX6675
  input = thermocouple.readCelsius();
  
  // Check for sensor errors
  if(isnan(input)) {
    Serial.println("Error: Could not read temperature data");
    ledcWrite(pwmChannel, 0);  // Turn off heater on error
    delay(1000);
    return;
  }
  
  // Compute PID
  myPID.Compute();
  
  // Apply PWM to heater
  ledcWrite(pwmChannel, (int)output);
  
  // Print data to serial monitor every second
  if(millis() - lastPrint >= printInterval) {
    double error = setpoint - input;
    
    Serial.print(millis()/1000.0, 1);  // Time in seconds
    Serial.print("\t");
    Serial.print(input, 2);            // Current temperature
    Serial.print("\t\t");
    Serial.print(setpoint, 1);         // Setpoint
    Serial.print("\t\t");
    Serial.print((int)output);         // PWM value
    Serial.print("\t");
    Serial.println(error, 2);          // Error
    
    lastPrint = millis();
  }
  
  // Check for serial commands
  if(Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if(command.startsWith("set ")) {
      double newSetpoint = command.substring(4).toDouble();
      if(newSetpoint > 0 && newSetpoint <= 300) {  // Safety limits
        setpoint = newSetpoint;
        Serial.print("Setpoint changed to: ");
        Serial.println(setpoint);
      } else {
        Serial.println("Invalid setpoint. Range: 0-300°C");
      }
    }
    else if(command.startsWith("kp ")) {
      kp = command.substring(3).toDouble();
      myPID.SetTunings(kp, ki, kd);
      Serial.print("Kp set to: ");
      Serial.println(kp);
    }
    else if(command.startsWith("ki ")) {
      ki = command.substring(3).toDouble();
      myPID.SetTunings(kp, ki, kd);
      Serial.print("Ki set to: ");
      Serial.println(ki);
    }
    else if(command.startsWith("kd ")) {
      kd = command.substring(3).toDouble();
      myPID.SetTunings(kp, ki, kd);
      Serial.print("Kd set to: ");
      Serial.println(kd);
    }
    else if(command == "auto") {
      myPID.SetMode(AUTOMATIC);
      Serial.println("PID set to AUTOMATIC mode");
    }
    else if(command == "manual") {
      myPID.SetMode(MANUAL);
      Serial.println("PID set to MANUAL mode");
    }
    else if(command.startsWith("pwm ")) {
      if(myPID.GetMode() == MANUAL) {
        int pwmValue = command.substring(4).toInt();
        if(pwmValue >= 0 && pwmValue <= 255) {
          output = pwmValue;
          ledcWrite(pwmChannel, pwmValue);
          Serial.print("Manual PWM set to: ");
          Serial.println(pwmValue);
        } else {
          Serial.println("PWM range: 0-255");
        }
      } else {
        Serial.println("Switch to manual mode first: 'manual'");
      }
    }
    else if(command == "status") {
      Serial.println("=== PID Status ===");
      Serial.print("Mode: ");
      Serial.println(myPID.GetMode() == AUTOMATIC ? "AUTOMATIC" : "MANUAL");
      Serial.print("Kp: "); Serial.println(kp);
      Serial.print("Ki: "); Serial.println(ki);
      Serial.print("Kd: "); Serial.println(kd);
      Serial.print("Current Temp: "); Serial.println(input);
      Serial.print("Setpoint: "); Serial.println(setpoint);
      Serial.print("Output: "); Serial.println(output);
    }
    else if(command == "help") {
      Serial.println("=== Available Commands ===");
      Serial.println("set [temp]   - Set target temperature (0-300°C)");
      Serial.println("kp [value]   - Set proportional gain");
      Serial.println("ki [value]   - Set integral gain");
      Serial.println("kd [value]   - Set derivative gain");
      Serial.println("auto         - Enable automatic PID control");
      Serial.println("manual       - Enable manual control");
      Serial.println("pwm [0-255]  - Set PWM manually (manual mode only)");
      Serial.println("status       - Show current PID status");
      Serial.println("help         - Show this help");
    }
    else {
      Serial.println("Unknown command. Type 'help' for available commands.");
    }
  }
  
  // Small delay
  delay(50);
}