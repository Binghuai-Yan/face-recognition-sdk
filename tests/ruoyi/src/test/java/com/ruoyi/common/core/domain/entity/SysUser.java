package com.ruoyi.common.core.domain.entity;
public class SysUser {
    private Long userId;
    private String status="0", delFlag="0", userName="alice";
    public Long getUserId() { return userId; }
    public void setUserId(Long id) { userId=id; }
    public String getStatus() { return status; }
    public void setStatus(String value) { status=value; }
    public String getDelFlag() { return delFlag; }
    public void setDelFlag(String value) { delFlag=value; }
    public String getUserName() { return userName; }
    public String getPassword() { return "sensitive-password"; }
}
