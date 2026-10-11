package com.ruoyi.common.core.domain;
import java.util.HashMap;
public class AjaxResult extends HashMap<String,Object> {
    public static AjaxResult success(String message) { return success(message,null); }
    public static AjaxResult success(String message,Object data) { AjaxResult r=new AjaxResult(); r.put("code",200); r.put("msg",message); r.put("data",data); return r; }
    public static AjaxResult error(String message) { AjaxResult r=new AjaxResult(); r.put("code",500); r.put("msg",message); return r; }
}
