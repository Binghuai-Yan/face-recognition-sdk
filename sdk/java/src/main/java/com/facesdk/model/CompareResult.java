/*
 * File: facesdk/sdk/java/src/main/java/com/facesdk/model/CompareResult.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * Compare Result Model
 */

package com.facesdk.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * 人脸比对结果
 *
 * @author FaceSDK Team
 * @version 1.0.0
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class CompareResult {

    @JsonProperty("similarity")
    private double similarity;

    @JsonProperty("distance")
    private double distance;

    @JsonProperty("threshold")
    private double threshold;

    @JsonProperty("is_match")
    private boolean match;

    @JsonProperty("face1")
    private Face face1;

    @JsonProperty("face2")
    private Face face2;

    public double getSimilarity() {
        return similarity;
    }

    public void setSimilarity(double similarity) {
        this.similarity = similarity;
    }

    public double getDistance() {
        return distance;
    }

    public void setDistance(double distance) {
        this.distance = distance;
    }

    public double getThreshold() {
        return threshold;
    }

    public void setThreshold(double threshold) {
        this.threshold = threshold;
    }

    public boolean isMatch() {
        return match;
    }

    public void setMatch(boolean match) {
        this.match = match;
    }

    public Face getFace1() {
        return face1;
    }

    public void setFace1(Face face1) {
        this.face1 = face1;
    }

    public Face getFace2() {
        return face2;
    }

    public void setFace2(Face face2) {
        this.face2 = face2;
    }

    @Override
    public String toString() {
        return "CompareResult{" +
                "similarity=" + similarity +
                ", distance=" + distance +
                ", threshold=" + threshold +
                ", match=" + match +
                ", face1=" + face1 +
                ", face2=" + face2 +
                '}';
    }
}
