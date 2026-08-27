package com.waterdetection.harness;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
class HarnessControllerTest {
    @Autowired
    private MockMvc mvc;

    @Test
    void duplicateEventRevisionIsIdempotent() throws Exception {
        String event = """
                {"event_id":"evt-1","event_revision":1,"event_status":"confirmed","event_type":"water_drop","camera_id":"cam-1"}
                """;
        mvc.perform(post("/mock/vision-events").contentType(MediaType.APPLICATION_JSON).content(event))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.duplicate").value(false));
        mvc.perform(post("/mock/vision-events").contentType(MediaType.APPLICATION_JSON).content(event))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.duplicate").value(true));
        mvc.perform(get("/mock/vision-events"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].event_id").value("evt-1"));
    }
}
