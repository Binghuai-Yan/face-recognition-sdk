/*
 * File: facesdk/examples/ruoyi-integration/FaceController.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * Ruoyi 框架人脸识别控制器
 */

package com.ruoyi.facesdk.controller;

import com.ruoyi.common.annotation.Log;
import com.ruoyi.common.core.controller.BaseController;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.enums.BusinessType;
import com.ruoyi.facesdk.service.FaceService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

/**
 * 人脸识别控制器
 * 提供人脸注册、人脸登录、人脸比对等功能
 */
@RestController
@RequestMapping("/face")
public class FaceController extends BaseController {

    @Autowired
    private FaceService faceService;

    /**
     * 人脸注册
     *
     * @param file     人脸图片
     * @param userId   用户ID
     * @param userName 用户名称
     * @return 注册结果
     */
    @Log(title = "人脸识别", businessType = BusinessType.INSERT)
    @PostMapping("/register")
    public AjaxResult register(
            @RequestParam("file") MultipartFile file,
            @RequestParam("userId") String userId,
            @RequestParam("userName") String userName) {
        try {
            return faceService.registerFace(file, userId, userName);
        } catch (Exception e) {
            logger.error("人脸注册失败", e);
            return AjaxResult.error("人脸注册失败: " + e.getMessage());
        }
    }

    /**
     * 人脸登录
     *
     * @param file 人脸图片
     * @return 登录结果
     */
    @Log(title = "人脸识别", businessType = BusinessType.OTHER)
    @PostMapping("/login")
    public AjaxResult login(@RequestParam("file") MultipartFile file) {
        try {
            return faceService.loginByFace(file);
        } catch (Exception e) {
            logger.error("人脸登录失败", e);
            return AjaxResult.error("人脸登录失败: " + e.getMessage());
        }
    }

    /**
     * 人脸比对
     *
     * @param file1 第一张图片
     * @param file2 第二张图片
     * @return 比对结果
     */
    @Log(title = "人脸识别", businessType = BusinessType.OTHER)
    @PostMapping("/compare")
    public AjaxResult compare(
            @RequestParam("file1") MultipartFile file1,
            @RequestParam("file2") MultipartFile file2) {
        try {
            return faceService.compareFaces(file1, file2);
        } catch (Exception e) {
            logger.error("人脸比对失败", e);
            return AjaxResult.error("人脸比对失败: " + e.getMessage());
        }
    }

    /**
     * 人脸检测
     *
     * @param file 图片文件
     * @return 检测结果
     */
    @Log(title = "人脸识别", businessType = BusinessType.OTHER)
    @PostMapping("/detect")
    public AjaxResult detect(@RequestParam("file") MultipartFile file) {
        try {
            return faceService.detectFace(file);
        } catch (Exception e) {
            logger.error("人脸检测失败", e);
            return AjaxResult.error("人脸检测失败: " + e.getMessage());
        }
    }

    /**
     * 删除人脸
     *
     * @param userId 用户ID
     * @return 删除结果
     */
    @Log(title = "人脸识别", businessType = BusinessType.DELETE)
    @DeleteMapping("/delete/{userId}")
    public AjaxResult deleteFace(@PathVariable("userId") String userId) {
        try {
            return faceService.deleteFace(userId);
        } catch (Exception e) {
            logger.error("删除人脸失败", e);
            return AjaxResult.error("删除人脸失败: " + e.getMessage());
        }
    }

    /**
     * 验证人脸是否已注册
     *
     * @param userId 用户ID
     * @return 验证结果
     */
    @GetMapping("/check/{userId}")
    public AjaxResult checkFace(@PathVariable("userId") String userId) {
        try {
            return faceService.checkFaceExists(userId);
        } catch (Exception e) {
            logger.error("检查人脸失败", e);
            return AjaxResult.error("检查人脸失败: " + e.getMessage());
        }
    }
}
