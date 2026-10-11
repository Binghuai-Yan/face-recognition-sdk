import com.facesdk.FaceSDK;
import com.facesdk.client.FaceSDKClient;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.Base64;
import java.util.UUID;

public class LiveSmoke {
    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        byte[] image = Files.readAllBytes(Path.of(System.getenv("FACESDK_TEST_IMAGE")));
        try (FaceSDK sdk = FaceSDK.builder().apiUrl(System.getenv("FACESDK_API_URL"))
                .detectionApiKey(System.getenv("FACESDK_DETECTION_API_KEY"))
                .recognitionApiKey(System.getenv("FACESDK_RECOGNITION_API_KEY"))
                .verificationApiKey(System.getenv("FACESDK_VERIFICATION_API_KEY"))
                .readTimeout(Duration.ofSeconds(120)).maxRetries(0).build()) {
            FaceSDKClient client = sdk.getClient();
            String subject = "facesdk-java-"+UUID.randomUUID();
            boolean cleanup = false;
            try {
                require(client.detect(image).getFaceCount()==1, "single face detection");
                require(client.createSubject(subject, "").getSubjectId().equals(subject), "create subject");
                cleanup = true;
                require(client.listSubjects().stream().anyMatch(s -> s.getSubjectId().equals(subject)), "list subject");
                var record = client.addFace(subject, image, null);
                require(record.getSubjectId().equals(subject) && !record.getImageId().isEmpty(), "add face");
                var result = client.search(image, 100, 0.8);
                require(result.getFaceCount()==1 && result.getResults().stream().anyMatch(r -> r.getSubjectId().equals(subject) && r.isMatch()), "recognize subject");
                var comparison = client.compare(image, image);
                require(comparison.isMatch() && comparison.getSimilarity()>=0.8, "self comparison");
                byte[] feature = Base64.getDecoder().decode(client.extractFeature(image));
                require(feature.length>0 && feature.length%4==0, "float32 feature");
                String expected = System.getenv("FACESDK_FEATURE_SHA256");
                if (expected != null) {
                    StringBuilder hex = new StringBuilder();
                    for (byte b : MessageDigest.getInstance("SHA-256").digest(feature)) hex.append(String.format("%02x", b & 255));
                    require(hex.toString().equals(expected), "cross-language embedding");
                }
                client.deleteFace(record.getImageId());
                if (client.listSubjects().stream().noneMatch(s -> s.getSubjectId().equals(subject))) client.createSubject(subject, "");
                client.deleteSubject(subject);
                cleanup = false;
                require(client.listSubjects().stream().noneMatch(s -> s.getSubjectId().equals(subject)), "delete subject");
                System.out.println("Java real-model lifecycle passed");
            } finally {
                if (cleanup) client.deleteSubject(subject);
            }
        }
    }
}
