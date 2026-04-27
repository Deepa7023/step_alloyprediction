'use client';

import React, { Suspense, useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Center, ContactShadows, Environment, Float, Grid, OrbitControls, Sparkles } from '@react-three/drei';
import { BufferGeometry, Group, Mesh } from 'three';
import { STLLoader } from 'three-stdlib';

interface CadDiagnostics {
  file?: string;
  engine?: string;
  dimensions?: {
    x?: number;
    y?: number;
    z?: number;
  };
  volume?: number;
  surfaceArea?: number;
  projectedArea?: number;
  topology?: {
    solids?: number;
    faces?: number;
    edges?: number;
    vertices?: number;
  };
  validation?: {
    is_manifold?: boolean;
    integrity_score?: number;
  };
}

const metric = (value?: number, digits = 2) => (
  typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : 'n/a'
);

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
      {/* Blueprint Wireframe Overlay */}
      <mesh geometry={geometry}>
        <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.06} />
      </mesh>
      
      {/* Main Casting Body (Premium Metal PBR) */}
      <mesh geometry={geometry} castShadow receiveShadow>
        <meshStandardMaterial
          color="#d1d9d4"
          metalness={0.92}
          roughness={0.12}
          envMapIntensity={1.2}
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

function RealCadDiagnostics({ diagnostics }: { diagnostics?: CadDiagnostics }) {
  const dimensions = diagnostics?.dimensions || {};
  const topology = diagnostics?.topology || {};
  const validation = diagnostics?.validation || {};
  const hasRealNumbers = Boolean(
    diagnostics?.volume ||
    diagnostics?.surfaceArea ||
    dimensions.x ||
    dimensions.y ||
    dimensions.z ||
    topology.faces ||
    topology.vertices
  );

  return (
    <div className="cad-real-diagnostics">
      <div className="cad-diagnostic-header">
        <span>CAD extraction completed</span>
        <strong>{diagnostics?.file || 'Uploaded geometry'}</strong>
        <p>
          {hasRealNumbers
            ? 'A renderable mesh was not returned, so this panel shows only measured data extracted from the uploaded CAD file.'
            : 'The backend did not return a renderable mesh or reliable geometry values for this file.'}
        </p>
      </div>

      <div className="cad-real-layout">
        <div className="cad-dimension-box" aria-label="Measured bounding box">
          <i style={{ width: `${Math.min(88, Math.max(24, Number(dimensions.x || 1)))}%` }} />
          <i style={{ height: `${Math.min(88, Math.max(24, Number(dimensions.z || 1)))}%` }} />
          <b />
          <span>X {metric(dimensions.x)} mm</span>
          <span>Y {metric(dimensions.y)} mm</span>
          <span>Z {metric(dimensions.z)} mm</span>
        </div>

        <div className="cad-real-metrics">
          <div>
            <span>Volume</span>
            <strong>{metric((diagnostics?.volume || 0) / 1000)} cm3</strong>
          </div>
          <div>
            <span>Surface area</span>
            <strong>{metric((diagnostics?.surfaceArea || 0) / 100)} cm2</strong>
          </div>
          <div>
            <span>Projected area</span>
            <strong>{metric(diagnostics?.projectedArea)} mm2</strong>
          </div>
          <div>
            <span>Engine</span>
            <strong>{diagnostics?.engine || 'Geometry parser'}</strong>
          </div>
          <div>
            <span>Topology</span>
            <strong>{topology.faces ?? 0} faces / {topology.vertices ?? 0} vertices</strong>
          </div>
          <div>
            <span>Integrity</span>
            <strong>{validation.integrity_score ?? 0}/100 {validation.is_manifold ? 'manifold' : 'checked'}</strong>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CADViewer({
  stlData,
  compact = false,
  diagnostics,
}: {
  stlData?: string;
  compact?: boolean;
  diagnostics?: CadDiagnostics;
}) {
  if (!stlData) {
    return (
      <div className={compact ? 'cad-viewer cad-viewer-compact cad-viewer-empty' : 'cad-viewer cad-viewer-empty'}>
        <RealCadDiagnostics diagnostics={diagnostics} />
      </div>
    );
  }

  return (
    <div className={compact ? 'cad-viewer cad-viewer-compact' : 'cad-viewer'}>
      <Canvas shadows camera={{ position: [110, 95, 110], fov: 32 }}>
        <color attach="background" args={['#080b0c']} />
        <Suspense fallback={null}>
          <Environment preset="studio" />
          <ambientLight intensity={0.4} />
          <spotLight position={[100, 100, 100]} angle={0.15} penumbra={1} intensity={1} castShadow />
          
          <Float speed={1.25} rotationIntensity={0.16} floatIntensity={0.28}>
            <Center>
              <CastingModel stlData={stlData} />
            </Center>
          </Float>

          <ContactShadows 
            position={[0, -25, 0]} 
            opacity={0.4} 
            scale={180} 
            blur={2.4} 
            far={40} 
          />
          
          <Sparkles count={45} speed={0.2} size={2} scale={[120, 76, 80]} color="#7dd5b8" />
          <ScanFrame />
        </Suspense>
        
        <OrbitControls makeDefault enablePan={false} minPolarAngle={0} maxPolarAngle={Math.PI / 1.75} />
        
        <Grid
          infiniteGrid
          fadeDistance={240}
          sectionColor="#2f6f4e"
          sectionSize={12}
          cellColor="#1a241f"
          cellSize={3}
          position={[0, -25.5, 0]}
        />
      </Canvas>
    </div>
  );
}
