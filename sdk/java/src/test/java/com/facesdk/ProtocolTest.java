package com.facesdk;

import com.facesdk.client.FaceSDKClient;
import com.facesdk.exception.FaceSDKException;
import com.facesdk.model.*;
import com.fasterxml.jackson.databind.*;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;

class ProtocolTest {
    HttpServer server;
    FaceSDK sdk;
    FaceSDKClient client;
    JsonNode fixtures;
    Queue<Reply> replies = new ArrayDeque<>();
    List<Recorded> requests = new ArrayList<>();
    static class Reply {
        int status; String body;
        Reply(int status, String body) { this.status=status; this.body=body; }
    }
    static class Recorded {
        String path, query, key, body, method;
    }
    void reply(int status, String fixture) { replies.add(new Reply(status, fixtures.get(fixture).toString())); }
    Recorded last() { return requests.get(requests.size()-1); }
    @BeforeEach void setUp() throws Exception {
        fixtures = new ObjectMapper().readTree(Files.readString(Path.of("../../tests/fixtures/compreface-1.2.json")));
        server = HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        server.createContext("/", exchange -> {
            Recorded r = new Recorded();
            r.path=exchange.getRequestURI().getRawPath(); r.query=exchange.getRequestURI().getRawQuery();
            r.key=exchange.getRequestHeaders().getFirst("x-api-key"); r.method=exchange.getRequestMethod();
            r.body=new String(exchange.getRequestBody().readAllBytes(),StandardCharsets.UTF_8);
            requests.add(r);
            Reply reply = replies.poll();
            if(reply==null) reply=new Reply(500,"{}");
            byte[] bytes=reply.body.getBytes(StandardCharsets.UTF_8);
            exchange.getResponseHeaders().set("Content-Type","application/json");
            exchange.sendResponseHeaders(reply.status, reply.status==204?-1:bytes.length);
            if(reply.status!=204) exchange.getResponseBody().write(bytes);
            exchange.close();
        });
        server.start();
        sdk=FaceSDK.builder().apiUrl("http://127.0.0.1:"+server.getAddress().getPort()+"/")
                .detectionApiKey("D").verificationApiKey("V").recognitionApiKey("R")
                .maxRetries(1).retryDelay(Duration.ZERO).build();
        client=sdk.getClient();
    }
    @AfterEach void tearDown() { client.close(); server.stop(0); }
    @Test void fullProtocol() throws Exception {
        byte[] image="complete-image".getBytes(StandardCharsets.UTF_8);
        reply(200,"detection"); DetectionResult detection=client.detect(image,Map.of("status",true,"det_prob_threshold",.7));
        assertEquals(1,detection.getFaceCount()); assertEquals(.99,detection.getFaces().get(0).getConfidence());
        assertEquals("D",last().key); assertTrue(last().query.contains("status=true")); assertTrue(last().body.contains("name=\"file\""));
        reply(200,"verification"); CompareResult comparison=client.compare(image,image);
        assertEquals(.8,comparison.getSimilarity()); assertTrue(comparison.isMatch()); assertEquals("V",last().key);
        assertEquals("/api/v1/verification/verify",last().path); assertTrue(last().body.contains("name=\"source_image\"")); assertTrue(last().body.contains("name=\"target_image\""));
        reply(200,"recognition"); SearchResult search=client.search(image,3,.8);
        assertEquals(1,search.getFaceCount()); assertEquals(2,search.getResults().size());
        assertEquals("best",search.getResults().get(0).getSubjectId()); assertEquals("boundary",search.getResults().get(1).getSubjectId());
        assertEquals("prediction_count=3",last().query); assertEquals("R",last().key);
        reply(200,"detection"); assertEquals(fixtures.get("embedding_base64").asText(),client.extractFeature(image));
        assertEquals("face_plugins=calculator",last().query);
        reply(200,"subjects"); assertEquals("张三 /?&",client.listSubjects().get(1).getSubjectId());
        String subject="张三 /?&";
        reply(201,"created"); assertEquals(subject,client.createSubject(subject,"ignored").getSubjectId());
        JsonNode body=new ObjectMapper().readTree(last().body); assertEquals(1,body.size()); assertEquals(subject,body.get("subject").asText());
        reply(201,"added"); FaceRecord face=client.addFace(subject,image,Map.of());
        assertEquals(fixtures.get("added").get("image_id").asText(),face.getImageId()); assertTrue(last().query.contains("%3F%26"));
        assertFalse(last().body.contains("metadata"));
        replies.add(new Reply(204,"")); client.deleteFace(face.getImageId());
        replies.add(new Reply(204,"")); client.deleteSubject(subject);
        assertTrue(last().path.contains("%2F%3F&") || last().path.contains("%2F%3F%26")); assertNull(last().query);
    }
    @Test void retriesReplayBody() {
        reply(503,"error"); reply(200,"detection");
        client.detect("complete-image".getBytes(StandardCharsets.UTF_8));
        assertEquals(2,requests.size()); assertEquals(requests.get(0).body,requests.get(1).body);
        assertTrue(last().body.contains("complete-image"));
    }
    @ParameterizedTest @ValueSource(ints={400,401}) void permanentErrorsAreNotRetried(int status) {
        reply(status,"error"); assertThrows(FaceSDKException.class,()->client.detect(new byte[0])); assertEquals(1,requests.size());
    }
    @Test void writesAreNotRetried() {
        reply(503,"error"); assertThrows(FaceSDKException.class,()->client.createSubject("new","")); assertEquals(1,requests.size());
        reply(503,"error"); assertThrows(FaceSDKException.class,()->client.addFace("new",new byte[0],null)); assertEquals(2,requests.size());
    }
    @ParameterizedTest @ValueSource(strings={"{}","[]","<html>bad</html>"}) void invalidPayloadDoesNotRetry(String body) {
        replies.add(new Reply(200,body)); assertThrows(FaceSDKException.class,()->client.detect(new byte[0])); assertEquals(1,requests.size());
    }
    @Test void invalidAndAmbiguousInput() {
        assertThrows(FaceSDKException.class,()->client.search(new byte[0],0,.8));
        assertThrows(FaceSDKException.class,()->client.search(new byte[0],1,Double.NaN));
        assertThrows(FaceSDKException.class,()->client.addFace("new",new byte[0],Map.of("source","camera")));
        assertThrows(FaceSDKException.class,()->client.deleteSubject("..")); assertTrue(requests.isEmpty());
        replies.add(new Reply(200,"{\"result\":[{},{}]}")); assertThrows(FaceSDKException.class,()->client.extractFeature(new byte[0]));
        reply(200,"empty"); assertThrows(FaceSDKException.class,()->client.compare(new byte[0],new byte[0]));
    }
    @Test void zeroRetriesAndSslBuilder() {
        try(FaceSDK zero=FaceSDK.builder().apiUrl("http://127.0.0.1:"+server.getAddress().getPort()).apiKey("key").maxRetries(0).verifySsl(false).build()) {
            reply(503,"error"); assertThrows(FaceSDKException.class,()->zero.getClient().detect(new byte[0])); assertEquals(1,requests.size());
        }
    }
}
