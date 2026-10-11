/*
 * File: facesdk/examples/ruoyi-integration/FaceService.java
 * Copyright (c) 2024 FaceSDK Contributors
 * MIT License
 *
 * Ruoyi 框架人脸识别服务
 */

package com.ruoyi.facesdk.service;

import com.facesdk.FaceSDK;
import com.facesdk.client.FaceSDKClient;
import com.facesdk.model.*;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.domain.entity.SysUser;
import com.ruoyi.system.service.ISysUserService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import javax.annotation.PostConstruct;
import java.io.IOException;
import com.ruoyi.common.utils.SecurityUtils;
import javax.annotation.PreDestroy;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * 人脸识别服务
 */
@Service
public class FaceService {

    private static final Logger logger = LoggerFactory.getLogger(FaceService.class);

    @Value("${facesdk.api-url}")
    private String apiUrl;

    @Value("${facesdk.detection-api-key}")
    private String detectionApiKey;
    @Value("${facesdk.recognition-api-key}")
    private String recognitionApiKey;
    @Value("${facesdk.verification-api-key}")
    private String verificationApiKey;
    @Value("${facesdk.connect-timeout:5000}")
    private long connectTimeout;
    @Value("${facesdk.read-timeout:30000}")
    private long readTimeout;

    @Value("${facesdk.similarity-threshold:0.8}")
    private double similarityThreshold;

    @Autowired
    private ISysUserService userService;

    private FaceSDKClient faceClient;

    /**
     * 初始化 FaceSDK 客户端
     */
    @PostConstruct
    public void init() {
        FaceSDK sdk = FaceSDK.builder()
                .apiUrl(apiUrl)
                .detectionApiKey(detectionApiKey)
                .recognitionApiKey(recognitionApiKey)
                .verificationApiKey(verificationApiKey)
                .comparisonThreshold(similarityThreshold)
                .connectTimeout(Duration.ofMillis(connectTimeout))
                .readTimeout(Duration.ofMillis(readTimeout))
                .build();
        this.faceClient = sdk.getClient();
        logger.info("FaceSDK client initialized");
    }

    /**
     * 人脸注册
     *
     * @param file     人脸图片
     * @param userId   用户ID
     * @param userName 用户名称
     * @return 注册结果
     */
    public AjaxResult registerFace(MultipartFile file, String userId, String userName) {
        requireOwner(userId);
        SysUser existingUser = userService.selectUserById(Long.valueOf(userId));
        if (!active(existingUser)) return AjaxResult.error("用户不存在或不可用");
        try {
            // 1. 检测人脸
            byte[] imageData = file.getBytes();
            DetectionResult detectionResult = faceClient.detect(imageData);

            if (detectionResult.getFaceCount() == 0) {
                return AjaxResult.error("未检测到人脸，请重新上传");
            }

            if (detectionResult.getFaceCount() > 1) {
                return AjaxResult.error("检测到多张人脸，请确保只有一张人脸");
            }

            // Adding a face creates the subject automatically.
            String subjectId = "user_" + userId;

            // CompreFace stores the subject and image ID; application metadata needs its own table.
            FaceRecord faceRecord = faceClient.addFace(subjectId, imageData, null);


            logger.info("Face registered successfully for user: {}", userId);
            return AjaxResult.success("人脸注册成功", faceRecord);

        } catch (IOException e) {
            logger.error("Failed to read image file", e);
            return AjaxResult.error("图片读取失败");
        } catch (Exception e) {
            logger.error("Face registration failed", e);
            return AjaxResult.error("人脸注册失败");
        }
    }

    /**
     * 人脸登录
     *
     * @param file 人脸图片
     * @return 登录结果
     */
    public AjaxResult loginByFace(MultipartFile file) {
        try {
            byte[] imageData = file.getBytes();

            // 1. 检测人脸
            DetectionResult detectionResult = faceClient.detect(imageData);
            if (detectionResult.getFaceCount() != 1) {
                return AjaxResult.error("请上传仅包含一张人脸的图片");
            }

            // 2. 在人脸库中搜索
            SearchResult searchResult = faceClient.search(imageData, 5, similarityThreshold);

            if (searchResult.getFaceCount() != 1 || searchResult.getResults() == null || searchResult.getResults().isEmpty()) {
                return AjaxResult.error("未找到匹配的人脸");
            }

            // 3. 获取最佳匹配
            SearchResult.MatchResult bestMatch = searchResult.getResults().get(0);

            if (!bestMatch.isMatch()) {
                return AjaxResult.error("人脸不匹配，请重试");
            }

            // 4. 提取用户ID
            String subjectId = bestMatch.getSubjectId();
            if (subjectId == null || !subjectId.matches("user_[0-9]+")) return AjaxResult.error("身份格式无效");
            String userId = subjectId.substring(5);
            requireOwner(userId);

            // 5. 查询用户信息
            SysUser user = userService.selectUserById(Long.valueOf(userId));
            if (!active(user)) {
                return AjaxResult.error("用户不存在或不可用");
            }

            logger.info("Face login successful for user: {}", userId);

            // 6. 返回登录成功结果（包含用户信息）
            Map<String, Object> result = new HashMap<>();
            result.put("userId", user.getUserId());
            result.put("userName", user.getUserName());
            result.put("verified", true);
            result.put("similarity", bestMatch.getSimilarity());

            return AjaxResult.success("人脸验证成功", result);

        } catch (IOException e) {
            logger.error("Failed to read image file", e);
            return AjaxResult.error("图片读取失败");
        } catch (Exception e) {
            logger.error("Face login failed", e);
            return AjaxResult.error("人脸登录失败");
        }
    }

    /**
     * 人脸比对
     *
     * @param file1 第一张图片
     * @param file2 第二张图片
     * @return 比对结果
     */
    public AjaxResult compareFaces(MultipartFile file1, MultipartFile file2) {
        try {
            byte[] imageData1 = file1.getBytes();
            byte[] imageData2 = file2.getBytes();

            CompareResult compareResult = faceClient.compare(imageData1, imageData2);

            Map<String, Object> result = new HashMap<>();
            result.put("similarity", compareResult.getSimilarity());
            result.put("distance", compareResult.getDistance());
            result.put("isMatch", compareResult.isMatch());
            result.put("threshold", compareResult.getThreshold());

            return AjaxResult.success("比对成功", result);

        } catch (IOException e) {
            logger.error("Failed to read image file", e);
            return AjaxResult.error("图片读取失败");
        } catch (Exception e) {
            logger.error("Face compare failed", e);
            return AjaxResult.error("人脸比对失败");
        }
    }

    /**
     * 人脸检测
     *
     * @param file 图片文件
     * @return 检测结果
     */
    public AjaxResult detectFace(MultipartFile file) {
        try {
            byte[] imageData = file.getBytes();
            DetectionResult detectionResult = faceClient.detect(imageData);

            Map<String, Object> result = new HashMap<>();
            result.put("faceCount", detectionResult.getFaceCount());
            result.put("faces", detectionResult.getFaces());

            return AjaxResult.success("检测成功", result);

        } catch (IOException e) {
            logger.error("Failed to read image file", e);
            return AjaxResult.error("图片读取失败");
        } catch (Exception e) {
            logger.error("Face detection failed", e);
            return AjaxResult.error("人脸检测失败");
        }
    }

    /**
     * 删除人脸
     *
     * @param userId 用户ID
     * @return 删除结果
     */
    public AjaxResult deleteFace(String userId) {
        requireOwner(userId);
        try {
            String subjectId = "user_" + userId;

            // 删除人脸库（会删除该用户所有人脸）
            faceClient.deleteSubject(subjectId);


            logger.info("Face deleted successfully for user: {}", userId);
            return AjaxResult.success("人脸删除成功");

        } catch (Exception e) {
            logger.error("Face deletion failed", e);
            return AjaxResult.error("人脸删除失败");
        }
    }

    /**
     * 检查人脸是否存在
     *
     * @param userId 用户ID
     * @return 检查结果
     */
    public AjaxResult checkFaceExists(String userId) {
        requireOwner(userId);
        try {
            String subjectId = "user_" + userId;

            // 获取所有人脸库
            List<Subject> subjects = faceClient.listSubjects();
            boolean exists = subjects.stream()
                    .anyMatch(s -> s.getSubjectId().equals(subjectId));

            return AjaxResult.success("查询成功", exists);

        } catch (Exception e) {
            logger.error("Face check failed", e);
            return AjaxResult.error("检查失败");
        }
    }
    private static void requireOwner(String userId) {
        Long actor = SecurityUtils.getUserId();
        if (actor == null || !actor.toString().equals(userId)) {
            throw new org.springframework.security.access.AccessDeniedException("只能管理本人绑定的人脸");
        }
    }

    private static boolean active(SysUser user) {
        return user != null && "0".equals(user.getStatus()) && "0".equals(user.getDelFlag());
    }

    @PreDestroy
    public void close() {
        if (faceClient != null) faceClient.close();
    }

}
