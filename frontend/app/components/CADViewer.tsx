'use client';

import React, { Suspense, useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Center, Float, Grid, OrbitControls, Sparkles, Stage } from '@react-three/drei';
import { BufferGeometry, Group, Mesh } from 'three';
import { STLLoader } from 'three-stdlib';

function parseStlData(url?: string) {
  if (!url) return null;

  try {
    const base64Data = url.split(',')[1];
    if (!base64Data) return null;

    const binaryData = atob(base64Data);
    const bytes = new Uint8Array(binaryData.length);
    for (let index = 0; index < binaryData.length; index += 1) {
      bytes[index] = binaryData.charCodeAt(index);
    }

    return new STLLoader().parse(bytes.buffer);
  } catch {
    return null;
  }
}

function CastingModel({ stlData }: { stlData?: string }) {
  const groupRef = useRef<Group>(null);
  const geometry = useMemo<BufferGeometry | null>(() => parseStlData(stlData), [stlData]);

  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.22;
      groupRef.current.rotation.x = Math.sin(Date.now() * 0.0006) * 0.08;
    }
  });

  if (!geometry) return null;

  return (
    <group ref={groupRef}>
      <mesh geometry={geometry} castShadow receiveShadow>
        <meshPhysicalMaterial
          color="#6f8f7a"
          metalness={0.82}
          roughness={0.2}
          clearcoat={0.35}
          clearcoatRoughness={0.28}
          envMapIntensity={1.5}
        />
      </mesh>
    </group>
  );
}

function ScanFrame() {
  const scanRef = useRef<Mesh>(null);

  useFrame(({ clock }) => {
    if (!scanRef.current) return;
    scanRef.current.position.y = Math.sin(clock.elapsedTime * 1.8) * 42;
  });

  return (
    <mesh ref={scanRef} rotation={[Math.PI / 2, 0, 0]}>
      <planeGeometry args={[120, 1.2]} />
      <meshBasicMaterial color="#b15f2a" transparent opacity={0.75} />
    </mesh>
  );
}

export default function CADViewer({ stlData, compact = false }: { stlData?: string; compact?: boolean }) {
  if (!stlData) {
    return (
      <div className={compact ? 'cad-viewer cad-viewer-compact cad-viewer-empty' : 'cad-viewer cad-viewer-empty'}>
        <div>
          <span>3D preview waits for uploaded CAD</span>
          <strong>No synthetic part shown</strong>
          <p>Upload a supported CAD file to render its actual extracted mesh.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={compact ? 'cad-viewer cad-viewer-compact' : 'cad-viewer'}>
      <Canvas shadows camera={{ position: [105, 86, 105], fov: 34 }}>
        <Suspense fallback={null}>
          <Stage environment="city" adjustCamera intensity={0.55}>
            <Float speed={1.25} rotationIntensity={0.16} floatIntensity={0.28}>
              <Center>
                <CastingModel stlData={stlData} />
              </Center>
            </Float>
          </Stage>
          <Sparkles count={80} speed={0.35} size={1.8} scale={[120, 76, 80]} color="#b15f2a" />
          <ScanFrame />
        </Suspense>
        <OrbitControls makeDefault enablePan={false} />
        <Grid
          infiniteGrid
          fadeDistance={260}
          sectionColor="#6f8f7a"
          sectionSize={12}
          cellColor="#d8ddd8"
          cellSize={3}
        />
      </Canvas>
    </div>
  );
}
