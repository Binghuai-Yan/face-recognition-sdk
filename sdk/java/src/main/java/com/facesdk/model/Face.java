/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/model/Face.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * Face Model
 */

package com.facesdk.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

/**
 * 人脸检测结果模型
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class Face {

    @JsonProperty("box")
    private BoundingBox boundingBox;

    @JsonProperty("landmarks")
    private List<List<Integer>> landmarks;

    @JsonProperty("confidence")
    private double confidence;

    @JsonProperty("quality")
    private Quality quality;

    public BoundingBox getBoundingBox() {
        return boundingBox;
    }

    public void setBoundingBox(BoundingBox boundingBox) {
        this.boundingBox = boundingBox;
    }

    public List<List<Integer>> getLandmarks() {
        return landmarks;
    }

    public void setLandmarks(List<List<Integer>> landmarks) {
        this.landmarks = landmarks;
    }

    public double getConfidence() {
        return confidence;
    }

    public void setConfidence(double confidence) {
        this.confidence = confidence;
    }

    public Quality getQuality() {
        return quality;
    }

    public void setQuality(Quality quality) {
        this.quality = quality;
    }

    @Override
    public String toString() {
        return "Face{" +
                "boundingBox=" + boundingBox +
                ", landmarks=" + landmarks +
                ", confidence=" + confidence +
                ", quality=" + quality +
                '}';
    }

    /**
     * 边界框
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class BoundingBox {
        @JsonProperty("x_min")
        private int xMin;
        @JsonProperty("y_min")
        private int yMin;
        @JsonProperty("x_max")
        private int xMax;
        @JsonProperty("y_max")
        private int yMax;

        public int getXMin() {
            return xMin;
        }

        public void setXMin(int xMin) {
            this.xMin = xMin;
        }

        public int getYMin() {
            return yMin;
        }

        public void setYMin(int yMin) {
            this.yMin = yMin;
        }

        public int getXMax() {
            return xMax;
        }

        public void setXMax(int xMax) {
            this.xMax = xMax;
        }

        public int getYMax() {
            return yMax;
        }

        public void setYMax(int yMax) {
            this.yMax = yMax;
        }

        @Override
        public String toString() {
            return "BoundingBox{" +
                    "xMin=" + xMin +
                    ", yMin=" + yMin +
                    ", xMax=" + xMax +
                    ", yMax=" + yMax +
                    '}';
        }
    }

    /**
     * 质量评分
     */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Quality {
        @JsonProperty("score")
        private double score;
        @JsonProperty("brightness")
        private double brightness;
        @JsonProperty("sharpness")
        private double sharpness;

        public double getScore() {
            return score;
        }

        public void setScore(double score) {
            this.score = score;
        }

        public double getBrightness() {
            return brightness;
        }

        public void setBrightness(double brightness) {
            this.brightness = brightness;
        }

        public double getSharpness() {
            return sharpness;
        }

        public void setSharpness(double sharpness) {
            this.sharpness = sharpness;
        }

        @Override
        public String toString() {
            return "Quality{" +
                    "score=" + score +
                    ", brightness=" + brightness +
                    ", sharpness=" + sharpness +
                    '}';
        }
    }
}
