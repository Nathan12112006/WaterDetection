package com.waterdetection.harness;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class VisionEventStore {
    private final Map<String, JsonNode> events = new ConcurrentHashMap<>();

    public boolean putIfAbsent(JsonNode event) {
        String eventId = requiredText(event, "event_id");
        int revision = event.path("event_revision").asInt(-1);
        if (revision < 1) {
            throw new IllegalArgumentException("event_revision must be at least 1");
        }
        return events.putIfAbsent(eventId + ":" + revision, event.deepCopy()) == null;
    }

    public List<JsonNode> findAll() {
        List<JsonNode> result = new ArrayList<>(events.values());
        result.sort(Comparator.comparing(node -> node.path("occurred_at").asText("")));
        return result;
    }

    private static String requiredText(JsonNode node, String field) {
        String value = node.path(field).asText("");
        if (value.isBlank()) {
            throw new IllegalArgumentException(field + " is required");
        }
        return value;
    }
}
