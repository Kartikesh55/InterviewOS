package com.interviewos.backend.integration.ai;

import java.time.Duration;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;

@Configuration
public class AiServiceConfiguration {
    @Bean
    RestClient aiServiceRestClient(
        RestClient.Builder builder,
        @Value("${ai.service.base-url}") String baseUrl,
        @Value("${ai.service.connect-timeout:3s}") Duration connectTimeout,
        @Value("${ai.service.read-timeout:120s}") Duration readTimeout
    ) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(connectTimeout);
        requestFactory.setReadTimeout(readTimeout);

        return builder
            .baseUrl(baseUrl)
            .requestFactory(requestFactory)
            .build();
    }
}
