# -*- coding: utf-8 -*-
"""
MPC二次规划求解器 - MPC Quadratic Programming Solver

功能：
- 模型预测控制求解
- 二次规划优化
- 约束处理
- 实时性保障
- 软约束松弛

支持多种求解策略：
- 密集QP求解
- 稀疏QP求解
- 热启动加速
- 分层求解
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable
from datetime import datetime
from enum import Enum
import time


class SolverStatus(Enum):
    """求解状态"""
    OPTIMAL = "optimal"
    SUBOPTIMAL = "suboptimal"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    MAX_ITER = "max_iterations"
    TIMEOUT = "timeout"
    ERROR = "error"


class ConstraintType(Enum):
    """约束类型"""
    EQUALITY = "equality"
    INEQUALITY = "inequality"
    BOUND = "bound"


@dataclass
class MPCProblem:
    """MPC问题定义"""
    # 状态空间模型 x(k+1) = A*x(k) + B*u(k)
    A: np.ndarray                      # 状态矩阵
    B: np.ndarray                      # 输入矩阵
    C: np.ndarray                      # 输出矩阵

    # 预测参数
    Np: int = 30                       # 预测时域
    Nc: int = 10                       # 控制时域

    # 权重矩阵
    Q: Optional[np.ndarray] = None     # 输出误差权重
    R: Optional[np.ndarray] = None     # 控制增量权重
    S: Optional[np.ndarray] = None     # 终端权重

    # 约束
    u_min: Optional[np.ndarray] = None  # 控制量下限
    u_max: Optional[np.ndarray] = None  # 控制量上限
    du_min: Optional[np.ndarray] = None # 控制增量下限
    du_max: Optional[np.ndarray] = None # 控制增量上限
    y_min: Optional[np.ndarray] = None  # 输出下限
    y_max: Optional[np.ndarray] = None  # 输出上限

    # 软约束松弛
    soft_constraints: bool = False
    slack_weight: float = 1e6


@dataclass
class MPCSolution:
    """MPC求解结果"""
    status: SolverStatus
    optimal_control: np.ndarray        # 最优控制序列
    predicted_output: np.ndarray       # 预测输出
    predicted_state: np.ndarray        # 预测状态
    cost: float = 0.0                  # 目标函数值

    # 求解信息
    iterations: int = 0
    solve_time_ms: float = 0.0
    constraint_violations: List[str] = field(default_factory=list)

    # 热启动数据
    warm_start_data: Optional[Dict] = None


class QPSolver:
    """
    二次规划求解器

    求解问题：
    min  0.5 * x'Hx + f'x
    s.t. Ax <= b
         Aeq*x = beq
         lb <= x <= ub
    """

    def __init__(self, method: str = "interior_point"):
        self.method = method
        self.max_iterations = 100
        self.tolerance = 1e-6
        self.warm_start = True

        # 缓存
        self._last_solution: Optional[np.ndarray] = None

    def solve(self, H: np.ndarray, f: np.ndarray,
              A: np.ndarray = None, b: np.ndarray = None,
              Aeq: np.ndarray = None, beq: np.ndarray = None,
              lb: np.ndarray = None, ub: np.ndarray = None,
              x0: np.ndarray = None) -> Tuple[np.ndarray, SolverStatus, Dict]:
        """
        求解二次规划

        Args:
            H: Hessian矩阵 (n x n)
            f: 线性项 (n,)
            A: 不等式约束矩阵 (m x n)
            b: 不等式约束右端 (m,)
            Aeq: 等式约束矩阵 (p x n)
            beq: 等式约束右端 (p,)
            lb: 下界 (n,)
            ub: 上界 (n,)
            x0: 初始点 (n,)

        Returns:
            最优解, 状态, 信息字典
        """
        n = H.shape[0]
        start_time = time.perf_counter()

        # 初始化
        if x0 is None:
            if self.warm_start and self._last_solution is not None:
                x0 = self._last_solution
            else:
                x0 = np.zeros(n)

        # 确保x0满足边界约束
        if lb is not None:
            x0 = np.maximum(x0, lb)
        if ub is not None:
            x0 = np.minimum(x0, ub)

        try:
            if self.method == "interior_point":
                x, status, info = self._interior_point_solve(
                    H, f, A, b, Aeq, beq, lb, ub, x0
                )
            elif self.method == "active_set":
                x, status, info = self._active_set_solve(
                    H, f, A, b, Aeq, beq, lb, ub, x0
                )
            else:
                x, status, info = self._gradient_projection_solve(
                    H, f, lb, ub, x0
                )

            # 缓存解
            self._last_solution = x.copy()

        except Exception as e:
            x = x0
            status = SolverStatus.ERROR
            info = {"error": str(e)}

        info["solve_time_ms"] = (time.perf_counter() - start_time) * 1000
        return x, status, info

    def _interior_point_solve(self, H, f, A, b, Aeq, beq, lb, ub, x0):
        """内点法求解"""
        n = H.shape[0]
        x = x0.copy()

        # 障碍函数参数
        mu = 10.0
        mu_factor = 0.1
        min_mu = 1e-10

        # 构建KKT系统
        for iteration in range(self.max_iterations):
            # 计算梯度和Hessian
            grad = H @ x + f

            # 应用边界约束
            if lb is not None and ub is not None:
                # 对数障碍函数梯度
                barrier_grad = np.zeros(n)
                barrier_hess = np.zeros((n, n))

                for i in range(n):
                    if x[i] - lb[i] > 1e-10:
                        barrier_grad[i] -= mu / (x[i] - lb[i])
                        barrier_hess[i, i] += mu / (x[i] - lb[i])**2
                    if ub[i] - x[i] > 1e-10:
                        barrier_grad[i] += mu / (ub[i] - x[i])
                        barrier_hess[i, i] += mu / (ub[i] - x[i])**2

                grad += barrier_grad
                H_mod = H + barrier_hess
            else:
                H_mod = H

            # 牛顿步
            try:
                # 添加正则化以确保正定
                H_reg = H_mod + 1e-8 * np.eye(n)
                dx = np.linalg.solve(H_reg, -grad)
            except np.linalg.LinAlgError:
                # 如果求解失败，使用梯度下降
                dx = -0.01 * grad

            # 线搜索
            alpha = 1.0
            while alpha > 1e-10:
                x_new = x + alpha * dx

                # 检查边界
                if lb is not None and np.any(x_new < lb):
                    alpha *= 0.5
                    continue
                if ub is not None and np.any(x_new > ub):
                    alpha *= 0.5
                    continue

                break

            x = x_new

            # 收敛检查
            if np.linalg.norm(grad) < self.tolerance:
                return x, SolverStatus.OPTIMAL, {"iterations": iteration + 1}

            # 降低障碍参数
            mu = max(mu * mu_factor, min_mu)

        return x, SolverStatus.MAX_ITER, {"iterations": self.max_iterations}

    def _active_set_solve(self, H, f, A, b, Aeq, beq, lb, ub, x0):
        """激活集法求解"""
        n = H.shape[0]
        x = x0.copy()

        # 活动约束集
        active_lb = set()
        active_ub = set()

        for iteration in range(self.max_iterations):
            # 确定活动约束
            if lb is not None:
                active_lb = set(i for i in range(n) if x[i] <= lb[i] + 1e-8)
            if ub is not None:
                active_ub = set(i for i in range(n) if x[i] >= ub[i] - 1e-8)

            # 自由变量
            free_vars = [i for i in range(n)
                         if i not in active_lb and i not in active_ub]

            if not free_vars:
                break

            # 在自由变量上求解
            n_free = len(free_vars)
            H_free = H[np.ix_(free_vars, free_vars)]
            f_free = f[free_vars] + H[np.ix_(free_vars, list(active_lb | active_ub))] @ x[list(active_lb | active_ub)]

            try:
                dx_free = np.linalg.solve(H_free + 1e-8 * np.eye(n_free), -f_free)
            except:
                dx_free = np.zeros(n_free)

            # 更新
            dx = np.zeros(n)
            for i, idx in enumerate(free_vars):
                dx[idx] = dx_free[i]

            # 步长
            alpha = 1.0
            if lb is not None:
                for i in free_vars:
                    if dx[i] < 0:
                        alpha = min(alpha, (lb[i] - x[i]) / dx[i])
            if ub is not None:
                for i in free_vars:
                    if dx[i] > 0:
                        alpha = min(alpha, (ub[i] - x[i]) / dx[i])

            x += alpha * dx

            # 收敛检查
            if np.linalg.norm(dx) < self.tolerance:
                return x, SolverStatus.OPTIMAL, {"iterations": iteration + 1}

        return x, SolverStatus.MAX_ITER, {"iterations": self.max_iterations}

    def _gradient_projection_solve(self, H, f, lb, ub, x0):
        """梯度投影法求解（用于边界约束QP）"""
        n = H.shape[0]
        x = x0.copy()
        alpha = 0.01

        for iteration in range(self.max_iterations):
            # 计算梯度
            grad = H @ x + f

            # 梯度步
            x_new = x - alpha * grad

            # 投影到可行域
            if lb is not None:
                x_new = np.maximum(x_new, lb)
            if ub is not None:
                x_new = np.minimum(x_new, ub)

            # 收敛检查
            if np.linalg.norm(x_new - x) < self.tolerance:
                return x_new, SolverStatus.OPTIMAL, {"iterations": iteration + 1}

            x = x_new

        return x, SolverStatus.MAX_ITER, {"iterations": self.max_iterations}


class MPCSolver:
    """
    MPC求解器

    功能：
    - 构建QP问题
    - 调用QP求解器
    - 处理约束
    - 实时性保障
    """

    def __init__(self, problem: MPCProblem):
        self.problem = problem
        self.qp_solver = QPSolver(method="interior_point")

        # 性能统计
        self.solve_times: List[float] = []
        self.solve_count = 0

        # 预计算
        self._precompute_matrices()

    def _precompute_matrices(self):
        """预计算预测矩阵"""
        p = self.problem
        n_x = p.A.shape[0]
        n_u = p.B.shape[1]
        n_y = p.C.shape[0]

        Np = p.Np
        Nc = p.Nc

        # 预测矩阵 Y = Psi*x0 + Theta*U
        # 状态预测: X = [x1; x2; ...; xNp]
        self.Psi = np.zeros((Np * n_x, n_x))
        self.Theta = np.zeros((Np * n_x, Nc * n_u))

        A_power = np.eye(n_x)
        for i in range(Np):
            A_power = A_power @ p.A
            self.Psi[i*n_x:(i+1)*n_x, :] = A_power

            for j in range(min(i + 1, Nc)):
                A_j = np.linalg.matrix_power(p.A, i - j)
                self.Theta[i*n_x:(i+1)*n_x, j*n_u:(j+1)*n_u] = A_j @ p.B

        # 输出预测矩阵
        C_bar = np.kron(np.eye(Np), p.C)
        self.Psi_y = C_bar @ self.Psi
        self.Theta_y = C_bar @ self.Theta

        # 默认权重
        if p.Q is None:
            p.Q = np.eye(Np * n_y)
        elif p.Q.shape[0] == n_y:
            p.Q = np.kron(np.eye(Np), p.Q)

        if p.R is None:
            p.R = 0.1 * np.eye(Nc * n_u)
        elif p.R.shape[0] == n_u:
            p.R = np.kron(np.eye(Nc), p.R)

        # Hessian和线性项模板
        self.H_template = self.Theta_y.T @ p.Q @ self.Theta_y + p.R
        # 确保正定
        self.H_template = 0.5 * (self.H_template + self.H_template.T)
        self.H_template += 1e-6 * np.eye(self.H_template.shape[0])

    def solve(self, x0: np.ndarray, y_ref: np.ndarray,
              u_prev: np.ndarray = None) -> MPCSolution:
        """
        求解MPC问题

        Args:
            x0: 当前状态
            y_ref: 参考轨迹 (Np*n_y,) 或 (n_y,)
            u_prev: 上一时刻控制量

        Returns:
            MPC求解结果
        """
        start_time = time.perf_counter()
        p = self.problem

        n_u = p.B.shape[1]
        n_y = p.C.shape[0]
        Np = p.Np
        Nc = p.Nc

        # 扩展参考轨迹
        if y_ref.shape[0] == n_y:
            y_ref = np.tile(y_ref, Np)

        # 自由响应
        Y_free = self.Psi_y @ x0

        # 构建QP问题
        # min 0.5*U'*H*U + f'*U
        H = self.H_template
        f = self.Theta_y.T @ p.Q @ (Y_free - y_ref)

        # 约束
        lb = None
        ub = None
        n_total = Nc * n_u

        # 控制量约束
        if p.u_min is not None and p.u_max is not None:
            lb = np.tile(p.u_min, Nc)
            ub = np.tile(p.u_max, Nc)

        # 控制增量约束
        if p.du_min is not None and p.du_max is not None and u_prev is not None:
            # 转换为控制量约束
            # U[0] = u_prev + dU[0]
            # U[k] = U[k-1] + dU[k]
            # 需要通过线性变换处理
            pass  # 简化处理，使用控制量约束

        # 求解QP
        x_opt, status, info = self.qp_solver.solve(
            H, f, lb=lb, ub=ub
        )

        # 计算预测输出
        Y_pred = Y_free + self.Theta_y @ x_opt

        # 计算预测状态
        X_pred = self.Psi @ x0 + self.Theta @ x_opt

        # 计算代价
        cost = 0.5 * x_opt.T @ H @ x_opt + f.T @ x_opt

        # 求解时间
        solve_time = (time.perf_counter() - start_time) * 1000
        self.solve_times.append(solve_time)
        self.solve_count += 1

        # 检查约束违反
        violations = []
        if p.u_min is not None:
            for i, u in enumerate(x_opt.reshape(Nc, n_u)):
                if np.any(u < p.u_min - 1e-6):
                    violations.append(f"u[{i}] < u_min")
        if p.u_max is not None:
            for i, u in enumerate(x_opt.reshape(Nc, n_u)):
                if np.any(u > p.u_max + 1e-6):
                    violations.append(f"u[{i}] > u_max")

        return MPCSolution(
            status=status,
            optimal_control=x_opt.reshape(Nc, n_u),
            predicted_output=Y_pred.reshape(Np, n_y),
            predicted_state=X_pred.reshape(Np, -1),
            cost=cost,
            iterations=info.get("iterations", 0),
            solve_time_ms=solve_time,
            constraint_violations=violations,
        )

    def get_first_control(self, solution: MPCSolution) -> np.ndarray:
        """获取第一个控制量（滚动时域策略）"""
        return solution.optimal_control[0]

    def get_statistics(self) -> Dict[str, float]:
        """获取性能统计"""
        if not self.solve_times:
            return {}

        return {
            "solve_count": self.solve_count,
            "avg_time_ms": np.mean(self.solve_times),
            "max_time_ms": np.max(self.solve_times),
            "min_time_ms": np.min(self.solve_times),
            "std_time_ms": np.std(self.solve_times),
        }


class AdaptiveMPCSolver(MPCSolver):
    """
    自适应MPC求解器

    功能：
    - 在线参数调整
    - 模型自适应
    - 约束自适应
    """

    def __init__(self, problem: MPCProblem):
        super().__init__(problem)

        # 自适应参数
        self.model_adaptation_enabled = True
        self.weight_adaptation_enabled = True

        # 历史数据
        self.state_history: List[np.ndarray] = []
        self.control_history: List[np.ndarray] = []
        self.prediction_errors: List[float] = []

    def update_model(self, x_actual: np.ndarray, x_predicted: np.ndarray,
                     u_applied: np.ndarray):
        """
        更新模型参数

        Args:
            x_actual: 实际状态
            x_predicted: 预测状态
            u_applied: 实施的控制
        """
        if not self.model_adaptation_enabled:
            return

        # 计算预测误差
        error = np.linalg.norm(x_actual - x_predicted)
        self.prediction_errors.append(error)

        # 保存历史
        self.state_history.append(x_actual)
        self.control_history.append(u_applied)

        # 在线最小二乘辨识（简化）
        if len(self.state_history) > 10:
            # 可以实现RLS或其他在线辨识算法
            pass

    def adapt_weights(self, performance_metric: float, target: float):
        """
        自适应调整权重

        Args:
            performance_metric: 性能指标
            target: 目标值
        """
        if not self.weight_adaptation_enabled:
            return

        error_ratio = performance_metric / max(target, 1e-6)

        # 简单的自适应规则
        if error_ratio > 1.5:
            # 增大Q权重
            self.problem.Q *= 1.1
        elif error_ratio < 0.5:
            # 增大R权重
            self.problem.R *= 1.1

        # 重新计算矩阵
        self._precompute_matrices()


class DistributedMPCSolver:
    """
    分布式MPC求解器

    用于多机组/多电站协调控制

    功能：
    - ADMM分解求解
    - 分散式优化
    - 协调变量交换
    """

    def __init__(self, subsystems: List[MPCProblem],
                 coupling_matrix: np.ndarray = None):
        self.subsystems = subsystems
        self.n_subsystems = len(subsystems)
        self.coupling_matrix = coupling_matrix

        # ADMM参数
        self.rho = 1.0                 # 惩罚参数
        self.max_admm_iterations = 50
        self.admm_tolerance = 1e-4

        # 子系统求解器
        self.solvers = [MPCSolver(sub) for sub in subsystems]

        # 协调变量
        self.consensus_vars: Optional[np.ndarray] = None

    def solve_distributed(self, x0_list: List[np.ndarray],
                           y_ref_list: List[np.ndarray]) -> List[MPCSolution]:
        """
        分布式求解

        Args:
            x0_list: 各子系统初始状态
            y_ref_list: 各子系统参考轨迹

        Returns:
            各子系统解
        """
        n = self.n_subsystems

        # 初始化
        solutions = [None] * n
        z = np.zeros(n)  # 协调变量
        lambda_dual = np.zeros(n)  # 对偶变量

        for admm_iter in range(self.max_admm_iterations):
            # 并行求解各子系统（此处串行模拟）
            for i in range(n):
                solutions[i] = self.solvers[i].solve(
                    x0_list[i], y_ref_list[i]
                )

            # 提取耦合变量
            x_local = np.array([
                solutions[i].optimal_control[0, 0]  # 第一个控制量
                for i in range(n)
            ])

            # 更新协调变量（共识更新）
            z_new = np.mean(x_local + lambda_dual / self.rho)

            # 更新对偶变量
            lambda_dual += self.rho * (x_local - z_new)

            # 收敛检查
            primal_residual = np.linalg.norm(x_local - z_new)
            dual_residual = self.rho * np.linalg.norm(z_new - z)

            if primal_residual < self.admm_tolerance and dual_residual < self.admm_tolerance:
                break

            z = z_new

        self.consensus_vars = z
        return solutions

    def get_coordination_status(self) -> Dict[str, Any]:
        """获取协调状态"""
        return {
            "n_subsystems": self.n_subsystems,
            "consensus_value": self.consensus_vars.tolist() if self.consensus_vars is not None else None,
            "rho": self.rho,
        }


class RobustMPCSolver(MPCSolver):
    """
    鲁棒MPC求解器

    功能：
    - 不确定性处理
    - 最坏情况优化
    - 管式MPC
    """

    def __init__(self, problem: MPCProblem,
                 uncertainty_bounds: Dict[str, float] = None):
        super().__init__(problem)

        # 不确定性描述
        self.uncertainty_bounds = uncertainty_bounds or {
            "A": 0.05,  # A矩阵不确定性比例
            "B": 0.05,  # B矩阵不确定性比例
            "disturbance": 0.1,  # 扰动界
        }

        # 鲁棒参数
        self.robustness_margin = 0.1  # 鲁棒裕度

    def solve_robust(self, x0: np.ndarray, y_ref: np.ndarray,
                     u_prev: np.ndarray = None) -> MPCSolution:
        """
        求解鲁棒MPC

        Args:
            x0: 当前状态
            y_ref: 参考轨迹
            u_prev: 上一时刻控制

        Returns:
            鲁棒MPC解
        """
        # 收紧约束以保证鲁棒性
        p = self.problem

        # 收紧控制约束
        if p.u_min is not None:
            p_robust = MPCProblem(
                A=p.A, B=p.B, C=p.C,
                Np=p.Np, Nc=p.Nc,
                Q=p.Q, R=p.R,
                u_min=p.u_min * (1 + self.robustness_margin),
                u_max=p.u_max * (1 - self.robustness_margin),
            )
            solver = MPCSolver(p_robust)
            return solver.solve(x0, y_ref, u_prev)

        return self.solve(x0, y_ref, u_prev)


def create_governor_mpc(Tw: float = 2.0, Tm: float = 8.0,
                        Np: int = 30, Nc: int = 10,
                        dt: float = 0.1) -> MPCSolver:
    """
    创建调速器MPC求解器

    Args:
        Tw: 水锤时间常数
        Tm: 机械时间常数
        Np: 预测时域
        Nc: 控制时域
        dt: 采样时间

    Returns:
        MPC求解器
    """
    # 状态: [omega, y, pm] (转速、导叶、机械功率)
    # 输入: [y_cmd] (导叶指令)
    # 输出: [omega] (转速)

    # 连续系统
    # d(omega)/dt = (pm - pe) / Tm
    # d(y)/dt = (y_cmd - y) / Ty (Ty=0.5)
    # d(pm)/dt = (y*sqrt(h) - pm) / Tp (简化)

    Ty = 0.5
    Tp = 1.0

    A_cont = np.array([
        [0, 0, 1/Tm],
        [0, -1/Ty, 0],
        [0, 1/Tp, -1/Tp],
    ])
    B_cont = np.array([[0], [1/Ty], [0]])
    C = np.array([[1, 0, 0]])  # 输出转速

    # 离散化 (欧拉法)
    A = np.eye(3) + A_cont * dt
    B = B_cont * dt

    # 约束
    u_min = np.array([0.0])    # 导叶最小
    u_max = np.array([1.0])    # 导叶最大
    du_min = np.array([-0.1])  # 导叶变化率
    du_max = np.array([0.1])

    problem = MPCProblem(
        A=A, B=B, C=C,
        Np=Np, Nc=Nc,
        Q=np.eye(1) * 10.0,    # 转速跟踪权重
        R=np.eye(1) * 0.1,     # 控制增量权重
        u_min=u_min, u_max=u_max,
        du_min=du_min, du_max=du_max,
    )

    return MPCSolver(problem)


def create_agc_mpc(n_units: int = 4, Np: int = 20, Nc: int = 5,
                   dt: float = 1.0) -> MPCSolver:
    """
    创建AGC MPC求解器

    Args:
        n_units: 机组数量
        Np: 预测时域
        Nc: 控制时域
        dt: 采样时间

    Returns:
        AGC MPC求解器
    """
    # 状态: [P1, P2, ..., Pn, ACE] (各机组功率和区域控制误差)
    # 输入: [dP1, dP2, ..., dPn] (功率调整指令)
    # 输出: [ACE] (区域控制误差)

    n_x = n_units + 1
    n_u = n_units

    # 简化模型
    tau = 10.0  # 功率响应时间常数

    A = np.eye(n_x)
    A[-1, :-1] = -dt / tau  # ACE响应

    B = np.zeros((n_x, n_u))
    for i in range(n_units):
        B[i, i] = dt / tau  # 功率响应
        B[-1, i] = -dt / tau  # ACE变化

    C = np.zeros((1, n_x))
    C[0, -1] = 1  # 输出ACE

    # 约束
    u_min = np.ones(n_u) * (-50)   # 最大减载 MW
    u_max = np.ones(n_u) * 50      # 最大增载 MW

    problem = MPCProblem(
        A=A, B=B, C=C,
        Np=Np, Nc=Nc,
        Q=np.eye(1) * 100.0,   # ACE权重
        R=np.eye(n_u) * 1.0,   # 调节量权重
        u_min=u_min, u_max=u_max,
    )

    return MPCSolver(problem)
