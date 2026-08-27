package com.waterdetection.harness;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/mock")
public class HarnessController {
    private final VisionEventStore store;
    private final RestClient visionClient;

    public HarnessController(VisionEventStore store, @Value("${vision.base-url}") String visionBaseUrl) {
        this.store = store;
        this.visionClient = RestClient.builder().baseUrl(visionBaseUrl).build();
    }

    @PostMapping("/vision-events")
    public ResponseEntity<Map<String, Object>> receiveEvent(@RequestBody JsonNode event) {
        try {
            boolean inserted = store.putIfAbsent(event);
            return ResponseEntity.ok(Map.of("accepted", true, "duplicate", !inserted));
        } catch (IllegalArgumentException exc) {
            return ResponseEntity.badRequest().body(Map.of("accepted", false, "error", exc.getMessage()));
        }
    }

    @GetMapping("/vision-events")
    public List<JsonNode> receivedEvents() {
        return store.findAll();
    }

    @GetMapping(value = "/cameras/{cameraId}/raw", produces = MediaType.IMAGE_JPEG_VALUE)
    public ResponseEntity<byte[]> rawSnapshot(@PathVariable String cameraId) {
        return proxySnapshot(cameraId, false);
    }

    @GetMapping(value = "/cameras/{cameraId}/annotated", produces = MediaType.IMAGE_JPEG_VALUE)
    public ResponseEntity<byte[]> annotatedSnapshot(@PathVariable String cameraId) {
        return proxySnapshot(cameraId, true);
    }

    private ResponseEntity<byte[]> proxySnapshot(String cameraId, boolean annotated) {
        String path = annotated
                ? "/api/v1/cameras/{cameraId}/annotated-snapshot"
                : "/api/v1/cameras/{cameraId}/snapshot";
        try {
            ResponseEntity<byte[]> response = visionClient.get()
                    .uri(path, cameraId)
                    .retrieve()
                    .toEntity(byte[].class);
            return ResponseEntity.status(response.getStatusCode())
                    .contentType(MediaType.IMAGE_JPEG)
                    .body(response.getBody());
        } catch (RestClientException exc) {
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY).build();
        }
    }
}
