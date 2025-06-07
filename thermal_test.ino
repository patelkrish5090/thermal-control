#include <Wire.h>
#include <Adafruit_MLX90640.h>

Adafruit_MLX90640 mlx;

float frame[768];

void setup() {
    Serial.begin(115200);
    while (!Serial);

    Wire.begin(21,22);  //  SDA on 21, SCL on 22
    Wire.setClock(100000);

    if (!mlx.begin(MLX90640_I2CADDR_DEFAULT, &Wire)) {
        Serial.println("Failed to initialise, check wiring");
        while(1);
    }

    mlx.setMode(MLX90640_CHESS);
    mlx.setResolution(MLX90640_ADC_18BIT);
    mlx.setRefreshRate(MLX90640_4_HZ);
}

void loop(){

    int status = mlx.getFrame(frame);
    // if(status != 0) {
    //     Serial.println(status);
    //     return;
    // }

    for(int i = 0; i < 32*24; i++){
        Serial.print(frame[i]);
        Serial.print(", ");
    }
    Serial.println();
}