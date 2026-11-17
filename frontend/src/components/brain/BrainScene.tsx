import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF, Center, Html, Environment } from "@react-three/drei";
import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import type { BandInfo } from "../../data/types";
import "./BrainScene.css";

const MODEL_URL = "/models/brain.glb";

type Props = {
  bands: BandInfo[];
};

type ControlsHandle = {
  object: THREE.Camera;
  target: THREE.Vector3;
  update: () => void;
  reset: () => void;
};

/**
 * Plexus-style neural sphere (like the glass-orb reference):
 * fibonacci shell + nearest-neighbor triangles, multi-color nodes, cyan glow lines.
 * Brain sits in the center instead of a filled circle.
 */
function makeCirclePointTexture() {
  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.35, "rgba(255,255,255,0.85)");
  g.addColorStop(0.7, "rgba(255,255,255,0.25)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

function NeuralField({ intensity }: { intensity: number }) {
  const group = useRef<THREE.Group>(null);
  const lineMat = useRef<THREE.LineBasicMaterial>(null);
  const pointMat = useRef<THREE.PointsMaterial>(null);
  const circleMap = useMemo(() => makeCirclePointTexture(), []);

  const { positions, colors, linePositions, lineColors } = useMemo(() => {
    const n = 88;
    const radius = 1.58;
    const pts: THREE.Vector3[] = [];
    const golden = Math.PI * (3 - Math.sqrt(5)); // fibonacci sphere

    for (let i = 0; i < n; i++) {
      const y = 1 - (i / (n - 1)) * 2;
      const rad = Math.sqrt(Math.max(0, 1 - y * y));
      const theta = golden * i;
      // Slight ellipsoid so it wraps the brain shape
      pts.push(
        new THREE.Vector3(
          Math.cos(theta) * rad * radius * 1.08,
          y * radius * 0.9,
          Math.sin(theta) * rad * radius * 1.04
        )
      );
    }

    // Medical slide palette: icy blues + amber accents
    const palette = [
      new THREE.Color("#7ec8ff"),
      new THREE.Color("#a8dcff"),
      new THREE.Color("#3d7cff"),
      new THREE.Color("#5b9fff"),
      new THREE.Color("#ff8c2a"),
      new THREE.Color("#ffb347"),
      new THREE.Color("#d6ecff"),
      new THREE.Color("#4da6ff"),
    ];

    const pos = new Float32Array(n * 3);
    const col = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const p = pts[i]!;
      pos[i * 3] = p.x;
      pos[i * 3 + 1] = p.y;
      pos[i * 3 + 2] = p.z;
      const c = palette[i % palette.length]!;
      col[i * 3] = c.r;
      col[i * 3 + 1] = c.g;
      col[i * 3 + 2] = c.b;
    }

    // Local plexus — keep net outside the brain volume
    const kNear = 4;
    const maxDist = 0.85;
    const edgeKey = new Set<string>();
    const segs: number[] = [];
    const segCols: number[] = [];

    for (let i = 0; i < n; i++) {
      const dists: { j: number; d: number }[] = [];
      for (let j = 0; j < n; j++) {
        if (i === j) continue;
        dists.push({ j, d: pts[i]!.distanceTo(pts[j]!) });
      }
      dists.sort((a, b) => a.d - b.d);
      let linked = 0;
      for (const { j, d } of dists) {
        if (linked >= kNear || d > maxDist) break;
        const key = i < j ? `${i}-${j}` : `${j}-${i}`;
        if (edgeKey.has(key)) {
          linked += 1;
          continue;
        }
        edgeKey.add(key);
        linked += 1;
        const a = pts[i]!;
        const b = pts[j]!;
        segs.push(a.x, a.y, a.z, b.x, b.y, b.z);
        // Soft cyan-dominant lines with a hint of node color
        const ca = palette[i % palette.length]!;
        const cb = palette[j % palette.length]!;
        const mixA = ca.clone().lerp(new THREE.Color("#7ec8ff"), 0.65);
        const mixB = cb.clone().lerp(new THREE.Color("#7ec8ff"), 0.65);
        segCols.push(mixA.r, mixA.g, mixA.b, mixB.r, mixB.g, mixB.b);
      }
    }

    return {
      positions: pos,
      colors: col,
      linePositions: new Float32Array(segs),
      lineColors: new Float32Array(segCols),
    };
  }, []);

  useFrame(({ clock }, dt) => {
    if (group.current) {
      group.current.rotation.y += dt * 0.06;
    }
    const pulse = 0.5 + Math.sin(clock.elapsedTime * 0.9) * 0.12;
    if (lineMat.current) {
      lineMat.current.opacity = 0.22 + intensity * 0.25 + pulse * 0.08;
    }
    if (pointMat.current) {
      pointMat.current.size = 0.06 + intensity * 0.03 + pulse * 0.012;
    }
  });

  return (
    <group ref={group}>
      <lineSegments>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[linePositions, 3]} />
          <bufferAttribute attach="attributes-color" args={[lineColors, 3]} />
        </bufferGeometry>
        <lineBasicMaterial
          ref={lineMat}
          vertexColors
          transparent
          opacity={0.38}
          depthTest
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </lineSegments>
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
          <bufferAttribute attach="attributes-color" args={[colors, 3]} />
        </bufferGeometry>
        <pointsMaterial
          ref={pointMat}
          map={circleMap}
          vertexColors
          size={0.09}
          transparent
          opacity={0.95}
          sizeAttenuation
          depthTest
          depthWrite={false}
          blending={THREE.AdditiveBlending}
          alphaTest={0.02}
        />
      </points>
    </group>
  );
}

function AnatomicalBrain() {
  const { scene } = useGLTF(MODEL_URL);
  const group = useRef<THREE.Group>(null);

  const cloned = useMemo(() => {
    const root = scene.clone(true);
    root.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      mesh.castShadow = false;
      mesh.receiveShadow = false;
      const prev = mesh.material;
      const src = (Array.isArray(prev) ? prev[0] : prev) as THREE.MeshStandardMaterial | undefined;
      // Glass / X-ray medical organ look (like the heart reference)
      mesh.material = new THREE.MeshPhysicalMaterial({
        map: null,
        normalMap: src?.normalMap ?? null,
        normalScale: new THREE.Vector2(0.65, 0.65),
        color: new THREE.Color("#b8dcff"),
        roughness: 0.18,
        metalness: 0.0,
        transmission: 0.82,
        thickness: 1.35,
        ior: 1.4,
        transparent: true,
        opacity: 0.92,
        clearcoat: 0.7,
        clearcoatRoughness: 0.2,
        envMapIntensity: 1.2,
        attenuationColor: new THREE.Color("#5a9fd4"),
        attenuationDistance: 1.8,
        emissive: new THREE.Color("#1e4a72"),
        emissiveIntensity: 0.15,
        side: THREE.DoubleSide,
      });
    });
    return root;
  }, [scene]);

  useFrame((_, dt) => {
    if (group.current) group.current.rotation.y += dt * 0.035;
  });

  return (
    <group ref={group} scale={1.22}>
      <Center>
        <primitive object={cloned} />
      </Center>
      <pointLight position={[0.45, 0.15, 0.55]} intensity={0.9} color="#ff8c2a" distance={2.4} />
      <pointLight position={[-0.45, -0.1, -0.35]} intensity={0.5} color="#7ec8ff" distance={2.6} />
    </group>
  );
}

function CameraRig({
  controlsRef,
}: {
  controlsRef: React.MutableRefObject<ControlsHandle | null>;
}) {
  const { camera } = useThree();
  useEffect(() => {
    camera.position.set(0.15, 0.05, 2.7);
    camera.lookAt(0, 0, 0);
  }, [camera]);
  return (
    <OrbitControls
      ref={controlsRef as any}
      enablePan={false}
      minDistance={1.5}
      maxDistance={5}
      enableDamping
      dampingFactor={0.12}
      makeDefault
    />
  );
}

function LoaderFallback() {
  return (
    <Html center>
      <div className="brain-fallback">Loading brain…</div>
    </Html>
  );
}

function SceneInner({
  bands,
  controlsRef,
}: {
  bands: BandInfo[];
  controlsRef: React.MutableRefObject<ControlsHandle | null>;
}) {
  const gamma = bands.find((b) => b.id === "gamma")?.relative_power ?? 0.2;
  return (
    <>
      <color attach="background" args={["#07131f"]} />
      <ambientLight intensity={0.35} />
      <directionalLight position={[3.5, 3, 2]} intensity={1.5} color="#e8f4ff" />
      <directionalLight position={[-2.8, 1, -1.2]} intensity={0.55} color="#7ec8ff" />
      <pointLight position={[1.2, -0.6, 1.6]} intensity={0.7} color="#ff8c2a" />
      <Suspense fallback={<LoaderFallback />}>
        <Environment preset="studio" environmentIntensity={0.65} />
        <AnatomicalBrain />
      </Suspense>
      <NeuralField intensity={gamma} />
      <CameraRig controlsRef={controlsRef} />
    </>
  );
}

useGLTF.preload(MODEL_URL);

export function BrainScene({ bands }: Props) {
  const controlsRef = useRef<ControlsHandle | null>(null);
  const [tick, setTick] = useState(0);

  const zoom = (dir: 1 | -1) => {
    const c = controlsRef.current;
    if (!c) return;
    const cam = c.object;
    const target = c.target;
    const offset = cam.position.clone().sub(target);
    const dist = offset.length();
    const next = THREE.MathUtils.clamp(dist * (dir > 0 ? 0.85 : 1.18), 1.5, 5);
    offset.setLength(next);
    cam.position.copy(target).add(offset);
    c.update();
  };

  const reset = () => {
    const c = controlsRef.current;
    if (c) {
      c.reset();
      c.object.position.set(0.15, 0.05, 2.7);
      c.target.set(0, 0, 0);
      c.update();
    } else setTick((t) => t + 1);
  };

  return (
    <div className="brain-panel">
      <div className="brain-toolbar">
        <span>Neural overview</span>
        <div className="brain-actions">
          <button type="button" className="brain-zoom" onClick={() => zoom(1)} title="Zoom in">
            +
          </button>
          <button type="button" className="brain-zoom" onClick={() => zoom(-1)} title="Zoom out">
            −
          </button>
          <button type="button" className="brain-reset" onClick={reset} title="Reset camera">
            Reset
          </button>
        </div>
      </div>
      <div className="brain-canvas-wrap">
        <Canvas
          key={tick}
          dpr={[1, 1.5]}
          frameloop="always"
          performance={{ min: 0.5 }}
          camera={{ position: [0.2, 0.15, 2.55], fov: 38 }}
          gl={{
            antialias: true,
            alpha: true,
            powerPreference: "high-performance",
            stencil: false,
            depth: true,
          }}
        >
          <SceneInner bands={bands} controlsRef={controlsRef} />
        </Canvas>
      </div>
    </div>
  );
}
