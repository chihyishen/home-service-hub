package com.inventory.common.config;

import io.micrometer.observation.Observation;
import io.micrometer.observation.ObservationRegistry;
import lombok.RequiredArgsConstructor;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

@Aspect
@Component
@RequiredArgsConstructor
public class RepositoryObservationAspect {

    private final ObservationRegistry observationRegistry;

    // 攔截所有 repository 套件底下的介面方法呼叫
    @Around("execution(* com.inventory..repository..*.*(..))")
    public Object observeRepository(ProceedingJoinPoint joinPoint) throws Throwable {
        String className = joinPoint.getSignature().getDeclaringType().getSimpleName();
        String methodName = joinPoint.getSignature().getName();
        
        // 建立一個觀測 (Span)
        // name: 指標名稱 (Prometheus 用)
        // contextualName: 追蹤顯示名稱 (Tempo 用)
        return Observation.createNotStarted("repository.operation", observationRegistry)
                .contextualName("Layer: Repository") 
                .lowCardinalityKeyValue("repository.class", className)
                .lowCardinalityKeyValue("repository.method", methodName)
                .observeChecked(() -> joinPoint.proceed());
    }
}
