# -*- coding: utf-8 -*-
"""
场景生成与识别模块测试
Scenario Generation and Recognition Module Tests
"""

import pytest
import numpy as np


class TestScenarioGenerator:
    """场景生成器测试"""

    def test_load_rejection_scenario(self):
        """测试甩负荷场景生成"""
        from yjdt.scenarios.generator import ScenarioGenerator

        generator = ScenarioGenerator(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        scenario = generator.generate_load_rejection(
            initial_power=800.0,
            rejection_ratio=1.0,  # 全甩
            rejection_time=0.1
        )

        assert 'name' in scenario
        assert 'type' in scenario
        assert 'events' in scenario
        assert scenario['type'] == 'load_rejection'
        assert len(scenario['events']) > 0

    def test_startup_scenario(self):
        """测试启动场景生成"""
        from yjdt.scenarios.generator import ScenarioGenerator

        generator = ScenarioGenerator(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        scenario = generator.generate_startup(
            target_power=800.0,
            startup_mode="normal"
        )

        assert scenario['type'] == 'startup'
        assert 'phases' in scenario
        assert len(scenario['phases']) >= 3  # 至少包含预备、空载、并网

    def test_shutdown_scenario(self):
        """测试停机场景生成"""
        from yjdt.scenarios.generator import ScenarioGenerator

        generator = ScenarioGenerator(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        scenario = generator.generate_shutdown(
            initial_power=800.0,
            shutdown_mode="normal"
        )

        assert scenario['type'] == 'shutdown'
        assert 'phases' in scenario

    def test_fault_scenario(self):
        """测试故障场景生成"""
        from yjdt.scenarios.generator import ScenarioGenerator

        generator = ScenarioGenerator(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        scenario = generator.generate_fault(
            fault_type="sensor_failure",
            fault_location="pressure_sensor",
            fault_severity=0.8
        )

        assert scenario['type'] == 'fault'
        assert 'fault_info' in scenario
        assert scenario['fault_info']['type'] == 'sensor_failure'

    def test_extreme_scenario(self):
        """测试极端工况场景生成"""
        from yjdt.scenarios.generator import ScenarioGenerator

        generator = ScenarioGenerator(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        scenario = generator.generate_extreme(
            extreme_type="low_head",
            parameter_values={'head': 400.0}  # 低水头
        )

        assert scenario['type'] == 'extreme'
        assert 'conditions' in scenario

    def test_combined_scenario(self):
        """测试组合场景生成"""
        from yjdt.scenarios.generator import ScenarioGenerator

        generator = ScenarioGenerator(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        scenario = generator.generate_combined(
            base_scenario="load_change",
            overlay_events=[
                {'time': 5.0, 'type': 'sensor_fault', 'target': 'PT001'},
                {'time': 10.0, 'type': 'head_change', 'value': -20.0}
            ]
        )

        assert scenario['type'] == 'combined'
        assert len(scenario['events']) >= 2


class TestScenarioLibrary:
    """场景库测试"""

    def test_library_creation(self):
        """测试场景库创建"""
        from yjdt.scenarios.generator import ScenarioLibrary

        library = ScenarioLibrary()

        assert library is not None
        assert hasattr(library, 'scenarios')

    def test_add_scenario(self):
        """测试添加场景"""
        from yjdt.scenarios.generator import ScenarioLibrary, ScenarioGenerator

        library = ScenarioLibrary()
        generator = ScenarioGenerator(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        scenario = generator.generate_load_rejection(
            initial_power=800.0,
            rejection_ratio=0.5
        )

        library.add(scenario)

        assert len(library) == 1

    def test_query_scenarios(self):
        """测试场景查询"""
        from yjdt.scenarios.generator import ScenarioLibrary, ScenarioGenerator

        library = ScenarioLibrary()
        generator = ScenarioGenerator(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        # 添加多种场景
        library.add(generator.generate_load_rejection(800.0, 0.5))
        library.add(generator.generate_load_rejection(600.0, 1.0))
        library.add(generator.generate_startup(800.0))
        library.add(generator.generate_fault("sensor_failure", "PT001", 0.5))

        # 按类型查询
        rejection_scenarios = library.query(type="load_rejection")
        assert len(rejection_scenarios) == 2

        fault_scenarios = library.query(type="fault")
        assert len(fault_scenarios) == 1


class TestScenarioRecognizer:
    """场景识别器测试"""

    def test_recognizer_creation(self):
        """测试识别器创建"""
        from yjdt.scenarios.recognizer import ScenarioRecognizer

        recognizer = ScenarioRecognizer(
            model_type="random_forest",
            n_features=50
        )

        assert recognizer is not None

    def test_feature_extraction(self):
        """测试特征提取"""
        from yjdt.scenarios.recognizer import FeatureExtractor

        extractor = FeatureExtractor(
            window_size=100,
            features=['mean', 'std', 'max', 'min', 'trend']
        )

        # 模拟时间序列数据
        data = {
            'power': np.random.randn(200) * 50 + 800,
            'frequency': np.random.randn(200) * 0.1 + 50,
            'head': np.random.randn(200) * 5 + 480
        }

        features = extractor.extract(data)

        assert features is not None
        assert len(features) > 0

    def test_scenario_classification(self):
        """测试场景分类"""
        from yjdt.scenarios.recognizer import ScenarioRecognizer
        import numpy as np

        recognizer = ScenarioRecognizer(
            model_type="random_forest",
            n_features=20
        )

        # 创建训练数据
        n_samples = 100
        X_train = np.random.randn(n_samples, 20)
        y_train = np.random.randint(0, 4, n_samples)  # 4类场景

        # 训练
        recognizer.train(X_train, y_train)

        # 预测
        X_test = np.random.randn(10, 20)
        predictions = recognizer.predict(X_test)

        assert len(predictions) == 10
        assert all(0 <= p < 4 for p in predictions)

    def test_confidence_estimation(self):
        """测试置信度估计"""
        from yjdt.scenarios.recognizer import ScenarioRecognizer
        import numpy as np

        recognizer = ScenarioRecognizer(
            model_type="random_forest",
            n_features=20
        )

        # 训练
        X_train = np.random.randn(100, 20)
        y_train = np.random.randint(0, 3, 100)
        recognizer.train(X_train, y_train)

        # 预测带置信度
        X_test = np.random.randn(5, 20)
        predictions, confidences = recognizer.predict_with_confidence(X_test)

        assert len(confidences) == 5
        assert all(0 <= c <= 1 for c in confidences)


class TestAnomalyDetector:
    """异常检测器测试"""

    def test_anomaly_detector_creation(self):
        """测试异常检测器创建"""
        from yjdt.scenarios.recognizer import AnomalyDetector

        detector = AnomalyDetector(
            method="isolation_forest",
            contamination=0.1
        )

        assert detector is not None

    def test_anomaly_detection(self):
        """测试异常检测"""
        from yjdt.scenarios.recognizer import AnomalyDetector
        import numpy as np

        detector = AnomalyDetector(
            method="isolation_forest",
            contamination=0.1
        )

        # 正常数据训练
        X_normal = np.random.randn(100, 10) + np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        detector.fit(X_normal)

        # 检测异常
        X_test = np.vstack([
            np.random.randn(8, 10),  # 正常
            np.random.randn(2, 10) + 10  # 异常
        ])

        is_anomaly = detector.detect(X_test)

        assert len(is_anomaly) == 10
        # 至少应该检测到一些异常
        assert sum(is_anomaly) >= 1

    def test_online_anomaly_detection(self):
        """测试在线异常检测"""
        from yjdt.scenarios.recognizer import AnomalyDetector
        import numpy as np

        detector = AnomalyDetector(
            method="isolation_forest",
            contamination=0.05
        )

        # 训练
        X_train = np.random.randn(200, 5)
        detector.fit(X_train)

        # 模拟在线检测
        anomaly_count = 0
        for i in range(50):
            if i < 45:
                sample = np.random.randn(1, 5)  # 正常
            else:
                sample = np.random.randn(1, 5) + 5  # 异常

            is_anomaly = detector.detect_single(sample)
            if is_anomaly:
                anomaly_count += 1

        # 应该检测到一些异常
        assert anomaly_count >= 1


class TestScenarioIntegration:
    """场景系统集成测试"""

    def test_generate_and_recognize(self):
        """测试生成-识别流程"""
        from yjdt.scenarios.generator import ScenarioGenerator
        from yjdt.scenarios.recognizer import ScenarioRecognizer, FeatureExtractor
        import numpy as np

        # 生成场景
        generator = ScenarioGenerator(
            rated_power=1000.0,
            rated_head=480.0,
            rated_speed=100.0
        )

        # 生成多个场景并提取特征
        extractor = FeatureExtractor(window_size=50)
        recognizer = ScenarioRecognizer(model_type="random_forest", n_features=15)

        # 模拟训练数据
        X_train = []
        y_train = []

        for i in range(40):
            scenario_type = i % 4
            # 模拟不同场景的特征
            if scenario_type == 0:  # 正常
                features = np.random.randn(15) * 0.5
            elif scenario_type == 1:  # 甩负荷
                features = np.random.randn(15) * 0.5 + np.array([2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
            elif scenario_type == 2:  # 故障
                features = np.random.randn(15) * 0.5 + np.array([0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
            else:  # 极端
                features = np.random.randn(15) * 0.5 + np.array([0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

            X_train.append(features)
            y_train.append(scenario_type)

        X_train = np.array(X_train)
        y_train = np.array(y_train)

        # 训练识别器
        recognizer.train(X_train, y_train)

        # 测试识别
        test_features = np.random.randn(15) * 0.5 + np.array([2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        prediction = recognizer.predict(test_features.reshape(1, -1))

        assert prediction[0] == 1  # 应该识别为甩负荷


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
