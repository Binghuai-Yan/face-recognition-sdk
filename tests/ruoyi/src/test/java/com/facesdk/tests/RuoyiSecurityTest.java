package com.facesdk.tests;
import com.facesdk.client.FaceSDKClient;
import com.facesdk.model.*;
import com.ruoyi.common.core.domain.AjaxResult;
import com.ruoyi.common.core.domain.entity.SysUser;
import com.ruoyi.common.utils.SecurityUtils;
import com.ruoyi.facesdk.controller.FaceController;
import com.ruoyi.facesdk.service.FaceService;
import com.ruoyi.system.service.ISysUserService;
import org.junit.jupiter.api.*;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.multipart.MultipartFile;
import java.lang.reflect.Field;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class RuoyiSecurityTest {
    FaceService service;
    FaceSDKClient client;
    ISysUserService users;
    MultipartFile image;
    SysUser user;
    static void inject(Object target,String field,Object value) throws Exception { Field f=target.getClass().getDeclaredField(field); f.setAccessible(true); f.set(target,value); }
    @BeforeEach void setup() throws Exception {
        SecurityUtils.actor=42L;
        service=new FaceService(); client=mock(FaceSDKClient.class); users=mock(ISysUserService.class); image=mock(MultipartFile.class);
        inject(service,"faceClient",client); inject(service,"userService",users); inject(service,"similarityThreshold",.8);
        when(image.getBytes()).thenReturn(new byte[]{1,2,3});
        user=new SysUser(); user.setUserId(42L); when(users.selectUserById(42L)).thenReturn(user);
        DetectionResult detection=new DetectionResult(); detection.setFaceCount(1); when(client.detect(any(byte[].class))).thenReturn(detection);
        SearchResult result=new SearchResult(); result.setFaceCount(1);
        SearchResult.MatchResult match=new SearchResult.MatchResult(); match.setSubjectId("user_42"); match.setSimilarity(.9); match.setMatch(true); result.setResults(List.of(match));
        when(client.search(any(byte[].class),eq(5),eq(.8))).thenReturn(result);
    }
    @Test void unauthorizedTargetNeverReachesBackend() {
        assertThrows(AccessDeniedException.class,()->service.registerFace(image,"7","spoofed"));
        assertThrows(AccessDeniedException.class,()->service.deleteFace("7"));
        assertThrows(AccessDeniedException.class,()->service.checkFaceExists("7"));
        verifyNoInteractions(client,users);
        SecurityUtils.actor=null;
        assertThrows(AccessDeniedException.class,()->service.deleteFace("42"));
    }
    @Test void controllerUsesAuthenticatedIdAndRequiresAuthentication() throws Exception {
        assertEquals("isAuthenticated()",FaceController.class.getAnnotation(PreAuthorize.class).value());
        FaceController controller=new FaceController(); FaceService mockService=mock(FaceService.class); inject(controller,"faceService",mockService);
        when(mockService.registerFace(image,"42","")).thenReturn(AjaxResult.success("ok"));
        assertEquals(500,controller.register(image,"7","fake").get("code")); verifyNoInteractions(mockService);
        controller.register(image,null,"fake"); verify(mockService).registerFace(image,"42","");
    }
    @Test void registrationDoesNotSendUnsupportedMetadataOrOverwriteRemark() {
        when(client.addFace(eq("user_42"),any(byte[].class),isNull())).thenReturn(new FaceRecord());
        assertEquals(200,service.registerFace(image,"42","fake").get("code"));
        verify(client).addFace(eq("user_42"),any(byte[].class),isNull()); verify(client,never()).createSubject(anyString(),anyString());
        verify(users).selectUserById(42L); verifyNoMoreInteractions(users);
    }
    @Test void disabledAndDeletedUsersCannotVerify() {
        user.setStatus("1"); assertEquals(500,service.loginByFace(image).get("code"));
        user.setStatus("0"); user.setDelFlag("2"); assertEquals(500,service.loginByFace(image).get("code"));
        assertEquals(500,service.registerFace(image,"42","").get("code"));
    }
    @Test void verificationRejectsMultipleFaces() {
        DetectionResult detection=new DetectionResult(); detection.setFaceCount(2); when(client.detect(any(byte[].class))).thenReturn(detection);
        assertEquals(500,service.loginByFace(image).get("code")); verify(client,never()).search(any(byte[].class),anyInt(),anyDouble());
    }
    @Test void verificationReturnsOnlySafeFieldsAndNoSession() {
        AjaxResult result=service.loginByFace(image); assertEquals(200,result.get("code"));
        Map<?,?> data=(Map<?,?>)result.get("data"); assertEquals(Set.of("userId","userName","verified","similarity"),data.keySet());
        assertEquals(42L,data.get("userId")); assertFalse(data.containsKey("user")); assertFalse(data.containsKey("token"));
    }
}
